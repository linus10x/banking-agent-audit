"""Regression guards for the beat-the-shit security findings (committed).

Each test reproduces a finding from the adversarial security chamber and asserts
the hardened behavior. A failure here means a previously-closed bypass reopened.
"""

from __future__ import annotations

import functools
from dataclasses import replace
from pathlib import Path

import pytest

from banking_agent_audit.governance.audit_chain import (
    AuditChain,
    AuditChainTamperError,
    InMemoryWitnessRegister,
    _compute_genesis_hash,
)
from banking_agent_audit.governance.defcon import DEFCON, DEFCONMachine, DEFCONTransitionError
from banking_agent_audit.governance.effective_challenge_harness import (
    EffectiveChallengeHarness,
    IndependenceAttestation,
    Recommendation,
)
from banking_agent_audit.governance.sovereign_veto import (
    SovereignVeto,
    VetoNotAuthorizedError,
    VetoReason,
)
from banking_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
    NonCanonicalPayloadError,
)
from tests.conftest import StubAuthorizer

ET = AuditEventType.AGENT_ACTION
AL = AutonomyLevel.A2_DELEGATED


def _ev(payload: dict) -> AuditEvent:
    return AuditEvent(
        sequence=0,
        event_type=ET,
        autonomy_level=AL,
        agent_id="a",
        payload=payload,
        timestamp="t",
        prev_hash="0" * 64,
    )


# === B1 — canonical-JSON hash collisions are rejected at construction ====


def test_b1_non_str_dict_key_rejected() -> None:
    with pytest.raises(NonCanonicalPayloadError):
        _ev({1: "a"})  # int key would collide with {"1": "a"} under JSON


def test_b1_non_json_object_rejected_no_str_coercion() -> None:
    class Sneaky:
        def __str__(self) -> str:
            return "100"

    with pytest.raises(NonCanonicalPayloadError):
        _ev({"k": Sneaky()})  # must NOT silently str()-coerce to collide with "100"


def test_b1_non_finite_float_rejected() -> None:
    with pytest.raises(NonCanonicalPayloadError):
        _ev({"k": float("nan")})
    with pytest.raises(NonCanonicalPayloadError):
        _ev({"k": float("inf")})


def test_b1_tuple_normalized_to_list_round_trip_stable() -> None:
    ev = _ev({"k": (1, 2)}).with_hash()
    # tuple normalized to list; round-trip preserves the hash (no meaning drift).
    again = AuditEvent.from_dict(ev.to_dict())
    assert again.event_hash == ev.event_hash
    assert again.payload == {"k": [1, 2]}


# === B2 — regeneration guard fails closed + catches dangling injection ===


def test_b2_regeneration_guard_fails_closed_on_inconsistency() -> None:
    witness = InMemoryWitnessRegister()
    chain = AuditChain(deployer_id="bank-x", witness_register=witness)
    chain.append(ET, AL, "a", {"i": 0})
    chain.anchor_to_witness()
    # Forge: tamper an event so the chain is internally inconsistent.
    chain._store[0] = replace(chain._store[0], payload={"i": 999})
    assert chain.verify() is False
    # The regeneration check must fail closed (not pass on set-membership alone).
    assert chain.verify_regeneration_resistant() is False


def test_b2_dangling_stale_hash_injection_caught() -> None:
    witness = InMemoryWitnessRegister()
    chain = AuditChain(deployer_id="bank-x", witness_register=witness)
    chain.append(ET, AL, "a", {"i": 0})
    chain.anchor_to_witness()
    stale_head = witness.anchored_heads()[0]

    regen = AuditChain(deployer_id="bank-x", witness_register=witness)
    regen.append(ET, AL, "a", {"i": 1})
    # Inject a bare event carrying the stale anchored hash but no valid linkage.
    forged = replace(regen._store[-1], event_hash=stale_head)
    regen._store.append(forged)
    assert regen.verify_regeneration_resistant() is False  # verify() fails first


# === B3 — production self-clear by matching principal_id is rejected ======


def test_b3_production_principal_id_equals_agent_id_rejected() -> None:
    from banking_agent_audit.governance.sovereign_veto import Principal

    authorizer = StubAuthorizer(credentials={"tok": Principal("credit-agent", is_agent=False)})
    veto = SovereignVeto(agent_id="credit-agent", authorizer=authorizer, mode="production")
    veto.trigger(VetoReason.MANUAL, "x", "y")
    with pytest.raises(VetoNotAuthorizedError, match="own veto"):
        veto.clear("self", credential="tok")
    assert veto.is_vetoed is True


def test_b3b_any_agent_principal_rejected_even_if_different_id() -> None:
    # The is_agent guard is independently meaningful: NO agent principal may
    # clear a veto, even one whose id differs from the governed agent.
    from banking_agent_audit.governance.sovereign_veto import Principal

    authorizer = StubAuthorizer(credentials={"tok": Principal("other-agent", is_agent=True)})
    veto = SovereignVeto(agent_id="credit-agent", authorizer=authorizer, mode="production")
    veto.trigger(VetoReason.MANUAL, "x", "y")
    with pytest.raises(VetoNotAuthorizedError, match="agent principal"):
        veto.clear("by-another-agent", credential="tok")
    assert veto.is_vetoed is True


# === B4 — advisory self-clear via case/whitespace variants rejected =======


@pytest.mark.parametrize("variant", ["AgentX", " agentx ", "AGENTX", "agentx\t"])
def test_b4_advisory_self_clear_variants_rejected(variant: str) -> None:
    veto = SovereignVeto(agent_id="agentx")
    veto.trigger(VetoReason.MANUAL, "x", "y")
    with pytest.raises(VetoNotAuthorizedError, match="own veto"):
        veto.clear("self", operator_id=variant)


# === M1 — corrupt JSONL surfaces a tamper signal, not an opaque crash =====


def test_m1_truncated_ledger_raises_tamper(tmp_path: Path) -> None:
    log = tmp_path / "audit.jsonl"
    chain = AuditChain(log_file=log, deployer_id="bank-x", chain_creation_iso="t")
    chain.append(ET, AL, "a", {"i": 0})
    with log.open("a", encoding="utf-8") as fh:
        fh.write('{"sequence": 1, "truncated')  # partial line, no newline
    with pytest.raises(AuditChainTamperError, match="corrupt ledger"):
        AuditChain(log_file=log, deployer_id="bank-x", chain_creation_iso="t")


# === M2 — DEFCON rejects a raw int target ================================


def test_m2_defcon_rejects_raw_int() -> None:
    m = DEFCONMachine()
    with pytest.raises(DEFCONTransitionError, match="DEFCON"):
        m.manual_override(4, "x", operator_id="human")  # type: ignore[arg-type]


def test_m2_defcon_one_step_still_holds_with_enum() -> None:
    m = DEFCONMachine()
    m.manual_override(DEFCON.ALERT, "preempt", operator_id="human")
    assert m.current_level() is DEFCON.ALERT


# === N1 — genesis-seed delimiter cannot be smuggled across fields =========


def test_n1_genesis_delimiter_no_collision() -> None:
    assert _compute_genesis_hash("a", "b/c") != _compute_genesis_hash("a/b", "c")
    a = AuditChain(deployer_id="a", chain_creation_iso="b/c")
    b = AuditChain(deployer_id="a/b", chain_creation_iso="c")
    assert a.genesis_seed() != b.genesis_seed()


# === N3 — self-challenge via functools.partial / wraps is rejected ========


def test_n3_partial_self_challenge_rejected() -> None:
    def primary(x: int) -> int:
        return x

    with pytest.raises(ValueError, match="same callable"):
        EffectiveChallengeHarness(
            primary_model=primary,
            challenger_model=functools.partial(primary),
            eval_set=[(1, 1)],
            independence=IndependenceAttestation("o", False, False, False),
            primary_id="m1",
            challenger_id="m2",
        )


def test_n3_wraps_self_challenge_rejected() -> None:
    def primary(x: int) -> int:
        return x

    @functools.wraps(primary)
    def wrapper(x: int) -> int:
        return primary(x)

    with pytest.raises(ValueError, match="same callable"):
        EffectiveChallengeHarness(
            primary_model=primary,
            challenger_model=wrapper,
            eval_set=[(1, 1)],
            independence=IndependenceAttestation("o", False, False, False),
            primary_id="m1",
            challenger_id="m2",
        )


# === D2 — independence detector overrides an "independent" attestation =====


def test_d2_detector_not_independent_overrides_attestation() -> None:
    class DenyDetector:
        def detect(self, primary_id: str, challenger_id: str, context: dict) -> bool | None:
            return False  # believes NOT independent

    report = EffectiveChallengeHarness(
        primary_model=lambda x: x,
        challenger_model=lambda x: x,  # perfect agreement
        eval_set=[(1, 1), (2, 2)],
        independence=IndependenceAttestation("o", False, False, False),  # attests independent
        primary_id="m1",
        challenger_id="m2",
        independence_detector=DenyDetector(),
    ).run()
    assert report.independent is False
    assert report.recommendation is Recommendation.ESCALATE


def test_d2_detector_abstain_uses_attestation() -> None:
    class AbstainDetector:
        def detect(self, primary_id: str, challenger_id: str, context: dict) -> bool | None:
            return None

    report = EffectiveChallengeHarness(
        primary_model=lambda x: x,
        challenger_model=lambda x: x,
        eval_set=[(1, 1), (2, 2)],
        independence=IndependenceAttestation("o", False, False, False),
        primary_id="m1",
        challenger_id="m2",
        independence_detector=AbstainDetector(),
    ).run()
    assert report.independent is True
    assert report.recommendation is Recommendation.ACCEPT_PRIMARY


# === Round-3 findings (final adversarial code review) ====================


def test_r3_mrm_report_must_match_model_id() -> None:
    """A passing report for one model cannot validate a different, un-challenged model."""
    from banking_agent_audit.governance.model_risk_management import (
        ModelRiskManagement,
        ModelRiskTier,
    )

    good = EffectiveChallengeHarness(
        primary_model=lambda x: x,
        challenger_model=lambda x: x,
        eval_set=[(1, 1), (2, 2)],
        independence=IndependenceAttestation("mrm", False, False, False),
        primary_id="model-good",
        challenger_id="challenger",
    ).run()
    mrm = ModelRiskManagement()
    mrm.register("model-bad", owner="owner", purpose="p", risk_tier=ModelRiskTier.TIER_1_HIGH)
    with pytest.raises(ValueError, match="does not match model_id"):
        mrm.record_validation("model-bad", good)  # replay attack
    assert mrm.approved_models() == []


def test_r3_mrm_matching_report_still_works() -> None:
    from banking_agent_audit.governance.model_risk_management import (
        ModelRiskManagement,
        ModelRiskTier,
        ValidationStatus,
    )

    report = EffectiveChallengeHarness(
        primary_model=lambda x: x,
        challenger_model=lambda x: x,
        eval_set=[(1, 1), (2, 2)],
        independence=IndependenceAttestation("mrm", False, False, False),
        primary_id="m1",
        challenger_id="challenger",
    ).run()
    mrm = ModelRiskManagement()
    mrm.register("m1", owner="owner", purpose="p", risk_tier=ModelRiskTier.TIER_1_HIGH)
    assert mrm.record_validation("m1", report) is ValidationStatus.APPROVED


def test_r3_sanctions_resolution_requires_auth_when_wired() -> None:
    from banking_agent_audit.governance.sanctions_workflow import (
        SanctionsDispositionWorkflow,
        SanctionsNotAuthorizedError,
        ScreeningMatch,
    )
    from banking_agent_audit.governance.sovereign_veto import Principal

    class Provider:
        source = "test"

        def screen(self, name: str, ctx: dict) -> list[ScreeningMatch]:
            return [ScreeningMatch(name, 0.99, self.source, {})] if name == "HIT" else []

    authorizer = StubAuthorizer(
        credentials={
            "officer": Principal("aml-officer", is_agent=False),
            "bot": Principal("bot", is_agent=True),
        },
        allowed_actions={"resolve_sanctions_case"},
    )
    wf = SanctionsDispositionWorkflow(list_provider=Provider(), authorizer=authorizer)
    case = wf.screen_and_dispose("c1", "HIT")
    # no credential -> rejected
    with pytest.raises(SanctionsNotAuthorizedError, match="credential is required"):
        wf.resolve_case(case.case_id, true_positive=False, reviewer_id="x")
    # agent principal -> rejected
    with pytest.raises(SanctionsNotAuthorizedError, match="agent principal"):
        wf.resolve_case(case.case_id, true_positive=False, reviewer_id="x", credential="bot")
    # forged -> rejected
    with pytest.raises(SanctionsNotAuthorizedError, match="authentication"):
        wf.resolve_case(case.case_id, true_positive=False, reviewer_id="x", credential="forged")
    # authenticated officer -> resolves
    resolved = wf.resolve_case(
        case.case_id, true_positive=False, reviewer_id="x", credential="officer"
    )
    assert resolved.state.value == "false_positive_cleared"


def test_r3_attester_verifier_normalizes_self_attestation() -> None:
    from banking_agent_audit.governance.autonomy_ladder import ControlAttestation
    from banking_agent_audit.reference_adapters import SingleAttesterVerifier
    from banking_agent_audit.schemas.audit_event import AutonomyLevel

    verifier = SingleAttesterVerifier(trusted_attesters={"AgentX"})
    att = ControlAttestation("c", AutonomyLevel.A1_ASSISTED, "AgentX", "s")
    # Case-variant of the agent's own id must still be caught as self-attestation.
    assert verifier.verify(att, " agentx ") is False


def test_r3_effective_challenge_normalizes_self_challenge() -> None:
    with pytest.raises(ValueError, match="self-challenge"):
        EffectiveChallengeHarness(
            primary_model=lambda x: x,
            challenger_model=lambda x: -x,
            eval_set=[(1, 1)],
            independence=IndependenceAttestation("o", False, False, False),
            primary_id="Model",
            challenger_id=" model ",  # case/whitespace variant
        )


def test_r3_riskmetrics_rejects_nan_and_inf() -> None:
    from banking_agent_audit.governance.defcon import RiskMetrics

    with pytest.raises(ValueError, match="finite"):
        RiskMetrics(portfolio_drawdown=float("nan"))
    with pytest.raises(ValueError, match="finite"):
        RiskMetrics(daily_loss=float("inf"))


def test_r3_anchor_empty_chain_raises() -> None:
    witness = InMemoryWitnessRegister()
    chain = AuditChain(deployer_id="bank-x", witness_register=witness)
    with pytest.raises(ValueError, match="empty chain"):
        chain.anchor_to_witness()
