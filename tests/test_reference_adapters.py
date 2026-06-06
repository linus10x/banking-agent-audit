"""Reference seam-adapter tests (the minimum-viable-production path)."""

from __future__ import annotations

from pathlib import Path

import pytest

from banking_agent_audit.governance.audit_chain import AuditChain
from banking_agent_audit.governance.autonomy_ladder import AutonomyLadder, ControlAttestation
from banking_agent_audit.governance.sovereign_veto import SovereignVeto, VetoReason
from banking_agent_audit.reference_adapters import (
    FileWitnessRegister,
    SignedTokenAuthorizer,
    SingleAttesterVerifier,
)
from banking_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel


def test_file_witness_is_durable(tmp_path: Path) -> None:
    path = tmp_path / "witness.jsonl"
    w1 = FileWitnessRegister(path)
    w1.anchor("head-abc", "2026-06-05T00:00:00+00:00")
    # A fresh instance (simulating restart) sees the anchored head.
    w2 = FileWitnessRegister(path)
    assert "head-abc" in w2.anchored_heads()


def test_file_witness_drives_regeneration_resistance(tmp_path: Path) -> None:
    witness = FileWitnessRegister(tmp_path / "w.jsonl")
    chain = AuditChain(deployer_id="small-bank", witness_register=witness, mode="production")
    chain.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A2_DELEGATED, "a", {"i": 1})
    chain.anchor_to_witness()
    assert chain.verify_regeneration_resistant() is True


def test_signed_token_authorizer_round_trip() -> None:
    auth = SignedTokenAuthorizer(b"deployer-secret", allowed_actions={"ciso": {"clear_veto"}})
    token = auth.issue("ciso", is_agent=False)
    principal = auth.authenticate(token)
    assert principal is not None
    assert principal.principal_id == "ciso"
    assert auth.authorize(principal, "clear_veto", {}) is True
    assert auth.authorize(principal, "other", {}) is False


def test_signed_token_forgery_rejected() -> None:
    auth = SignedTokenAuthorizer(b"deployer-secret")
    assert auth.authenticate("ciso:0:deadbeef") is None  # bad signature
    assert auth.authenticate("garbage") is None
    # A token signed by a DIFFERENT secret must not authenticate.
    other = SignedTokenAuthorizer(b"other-secret")
    assert auth.authenticate(other.issue("ciso")) is None


def test_empty_secret_rejected() -> None:
    with pytest.raises(ValueError, match="secret"):
        SignedTokenAuthorizer(b"")


def test_signed_token_authorizer_clears_a_production_veto() -> None:
    auth = SignedTokenAuthorizer(b"s", allowed_actions={"ciso": {"clear_veto"}})
    veto = SovereignVeto(agent_id="agent", authorizer=auth, mode="production")
    veto.trigger(VetoReason.MANUAL, "x", "y")
    veto.clear("resolved", credential=auth.issue("ciso"))
    assert veto.is_vetoed is False


def test_single_attester_verifier_rejects_self_and_untrusted() -> None:
    verifier = SingleAttesterVerifier(trusted_attesters={"external-auditor"})
    self_att = ControlAttestation("c", AutonomyLevel.A1_ASSISTED, "agent", "stmt")
    trusted_att = ControlAttestation("c", AutonomyLevel.A1_ASSISTED, "external-auditor", "stmt")
    untrusted_att = ControlAttestation("c", AutonomyLevel.A1_ASSISTED, "rando", "stmt")
    assert verifier.verify(self_att, "agent") is False
    assert verifier.verify(trusted_att, "agent") is True
    assert verifier.verify(untrusted_att, "agent") is False


def test_single_attester_verifier_in_production_gate() -> None:
    verifier = SingleAttesterVerifier(trusted_attesters={"external-auditor"})
    gate = AutonomyLadder(verifier=verifier, mode="production")
    atts = [
        ControlAttestation(
            "human_approval_workflow", AutonomyLevel.A1_ASSISTED, "external-auditor", "ok"
        )
    ]
    d = gate.evaluate_promotion(
        requesting_agent_id="agent",
        current_level=AutonomyLevel.A0_INFORMATIONAL,
        requested_level=AutonomyLevel.A1_ASSISTED,
        attestations=atts,
    )
    assert d.approved is True
    assert d.verified is True


def test_empty_trusted_set_rejected() -> None:
    with pytest.raises(ValueError, match="trusted attester"):
        SingleAttesterVerifier(trusted_attesters=set())
