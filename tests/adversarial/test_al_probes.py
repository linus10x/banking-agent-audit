"""The five AL-PROBES — committed reproductions of the catalog's failing
constructions, asserting the CORRECTED behavior holds on this library.

Each probe builds the exact construction that defeats a defective primitive and
asserts the defect is absent here. A PASS means the corrected guarantee holds:

* AL-PROBE-01 (P1): promote-without-lower-gates -> refused.
* AL-PROBE-02 (P2): veto un-self-clearable; clearing needs an authenticated human.
* AL-PROBE-03 (P3): a deployer-keyed (hardened) chain verifies True (no false
  TAMPER); in-place tamper detected; end-to-end regeneration detected.
* AL-PROBE-04 (P4): a one-call HALT -> NORMAL de-escalation fails safe.
* AL-PROBE-05 (P5): challenger == primary self-challenge rejected.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from banking_agent_audit.governance.audit_chain import (
    AuditChain,
    AuditChainTamperError,
    InMemoryWitnessRegister,
)
from banking_agent_audit.governance.autonomy_ladder import AutonomyLadder
from banking_agent_audit.governance.defcon import (
    DEFCON,
    DEFCONMachine,
    DEFCONTransitionError,
    RiskMetrics,
)
from banking_agent_audit.governance.effective_challenge_harness import (
    EffectiveChallengeHarness,
    IndependenceAttestation,
)
from banking_agent_audit.governance.sovereign_veto import (
    Principal,
    SovereignVeto,
    VetoNotAuthorizedError,
    VetoReason,
)
from banking_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel
from tests.conftest import StubAuthorizer, StubVerifier

ET = AuditEventType.AGENT_ACTION
AL = AutonomyLevel.A2_DELEGATED


# === AL-PROBE-01 — promote without lower gates is refused ================


def test_al_probe_01_promote_without_lower_gates_refused() -> None:
    """Attack: request A0 -> A4 with NO control attestations."""
    gate = AutonomyLadder(verifier=StubVerifier({"validator"}), mode="production")
    decision = gate.evaluate_promotion(
        requesting_agent_id="rogue-agent",
        current_level=AutonomyLevel.A0_INFORMATIONAL,
        requested_level=AutonomyLevel.A4_PRODUCTION_AUTONOMOUS,
        attestations=[],
    )
    assert decision.approved is False
    assert decision.granted_level == AutonomyLevel.A0_INFORMATIONAL
    assert decision.missing_controls  # lower gates are unmet


# === AL-PROBE-02 — veto is un-self-clearable; clear needs auth ===========


def test_al_probe_02_agent_cannot_self_clear_veto() -> None:
    """Attack: the vetoed agent presents its own (agent) credential to clear."""
    authorizer = StubAuthorizer(
        credentials={"agent-token": Principal("rogue-agent", is_agent=True)}
    )
    veto = SovereignVeto(agent_id="rogue-agent", authorizer=authorizer, mode="production")
    veto.trigger(VetoReason.RISK_LIMIT_BREACH, "monitor", "limit breach")
    with pytest.raises(VetoNotAuthorizedError):
        veto.clear("self-clear attempt", credential="agent-token")
    assert veto.is_vetoed is True


def test_al_probe_02b_unauthenticated_freestring_cannot_clear_in_production() -> None:
    """Attack: clear with a free-string operator_id (no credential) in production."""
    authorizer = StubAuthorizer(credentials={})
    veto = SovereignVeto(agent_id="agent", authorizer=authorizer, mode="production")
    veto.trigger(VetoReason.MANUAL, "x", "y")
    with pytest.raises(VetoNotAuthorizedError):
        veto.clear("ok", credential="anything-forged")
    assert veto.is_vetoed is True


# === AL-PROBE-03 — ledger: no false TAMPER; tamper + regen detected ======


def test_al_probe_03a_hardened_chain_does_not_false_tamper() -> None:
    """The defect being guarded: a clean deployer-keyed chain raising TAMPER.

    Build the exact failing construction — a deployer-keyed genesis event #0 —
    and assert it verifies True (the verifier branches the seed correctly).
    """
    from banking_agent_audit.governance.audit_chain import GENESIS_HASH, _compute_genesis_hash

    chain = AuditChain(deployer_id="bank-x", chain_creation_iso="2026-06-05T00:00:00+00:00")
    # The seed must actually be deployer-keyed (not the legacy zero-seed) — this is
    # the precise condition the original defect got wrong.
    assert chain.genesis_seed() == _compute_genesis_hash("bank-x", "2026-06-05T00:00:00+00:00")
    assert chain.genesis_seed() != GENESIS_HASH
    for i in range(5):
        chain.append(ET, AL, f"agent-{i}", {"i": i})
    assert chain.events()[0].prev_hash == chain.genesis_seed()  # entry #0 chains to the seed
    assert chain.verify() is True  # NO false TAMPER
    chain.verify_strict()  # does not raise


def test_al_probe_03b_inplace_tamper_detected() -> None:
    chain = AuditChain(deployer_id="bank-x")
    for i in range(4):
        chain.append(ET, AL, f"agent-{i}", {"i": i})
    chain._store[2] = replace(chain._store[2], payload={"i": 999})
    assert chain.verify() is False
    with pytest.raises(AuditChainTamperError):
        chain.verify_strict()


def test_al_probe_03c_end_to_end_regeneration_detected() -> None:
    witness = InMemoryWitnessRegister()
    chain = AuditChain(deployer_id="bank-x", witness_register=witness)
    for i in range(4):
        chain.append(ET, AL, f"agent-{i}", {"i": i})
    chain.anchor_to_witness()
    anchored_head = witness.anchored_heads()[0]

    regen = AuditChain(deployer_id="bank-x", witness_register=witness)
    for i in range(4):
        regen.append(ET, AL, f"agent-{i}", {"i": i})
    assert regen.verify() is True  # internally consistent
    assert anchored_head not in {e.event_hash for e in regen.events()}
    assert regen.verify_regeneration_resistant() is False  # regeneration caught


# === AL-PROBE-04 — illegal DEFCON transition fails safe ==================


def test_al_probe_04_one_call_halt_to_normal_refused() -> None:
    machine = DEFCONMachine()
    machine.evaluate(RiskMetrics(portfolio_drawdown=0.30))  # -> HALT
    assert machine.current_level() is DEFCON.HALT
    with pytest.raises(DEFCONTransitionError):
        machine.manual_override(DEFCON.NORMAL, "all clear", operator_id="human")
    assert machine.current_level() is DEFCON.HALT  # fails safe (stays HALT)


# === AL-PROBE-05 — self-challenge rejected ===============================


def test_al_probe_05_self_challenge_rejected() -> None:
    """Attack: a model owner sets challenger_id == primary_id to force agreement."""
    att = IndependenceAttestation(
        chosen_by="model-owner",
        same_owner=True,
        same_vendor_family=True,
        same_prompt_template=True,
    )
    with pytest.raises(ValueError, match="self-challenge"):
        EffectiveChallengeHarness(
            primary_model=lambda x: x,
            challenger_model=lambda x: x,
            eval_set=[(1, 1)],
            independence=att,
            primary_id="m1",
            challenger_id="m1",
        )


def test_al_probe_05b_owner_self_challenge_cannot_accept_primary() -> None:
    """Even with distinct ids, an un-attested-independent challenge cannot ACCEPT."""
    from banking_agent_audit.governance.effective_challenge_harness import Recommendation

    att = IndependenceAttestation(
        chosen_by="model-owner",
        same_owner=True,
        same_vendor_family=False,
        same_prompt_template=False,
    )
    report = EffectiveChallengeHarness(
        primary_model=lambda x: x,
        challenger_model=lambda x: x,  # perfect agreement
        eval_set=[(1, 1), (2, 2)],
        independence=att,
        primary_id="m1",
        challenger_id="m2",
    ).run()
    assert report.recommendation is not Recommendation.ACCEPT_PRIMARY
