"""P2 — sovereign veto tests (corrected: authenticated, un-self-clearable)."""

from __future__ import annotations

import pytest

from banking_agent_audit.governance.audit_chain import AuditChain
from banking_agent_audit.governance.sovereign_veto import (
    SovereignVeto,
    VetoNotAuthorizedError,
    VetoReason,
)
from tests.conftest import StubAuthorizer


def test_production_mode_requires_authorizer() -> None:
    with pytest.raises(ValueError, match="authorizer"):
        SovereignVeto(agent_id="a", mode="production")


def test_trigger_blocks_execution() -> None:
    v = SovereignVeto(agent_id="a")
    assert v.allow_execution() is True
    v.trigger(VetoReason.RISK_LIMIT_BREACH, "monitor", "dd breach")
    assert v.is_vetoed is True
    assert v.allow_execution() is False


def test_advisory_clear_requires_non_self_operator() -> None:
    v = SovereignVeto(agent_id="agent-a")
    v.trigger(VetoReason.MANUAL, "x", "y")
    with pytest.raises(VetoNotAuthorizedError, match="own veto"):
        v.clear("ok", operator_id="agent-a")  # self-clear refused
    rec = v.clear("ok", operator_id="human-ops")
    assert rec.cleared_by == "human-ops"
    assert rec.cleared_authenticated is False  # advisory, labeled


def test_production_clear_with_authenticated_human(authorizer: StubAuthorizer) -> None:
    v = SovereignVeto(agent_id="a", authorizer=authorizer, mode="production")
    v.trigger(VetoReason.SANCTIONS_HIT, "wf", "match")
    rec = v.clear("ok", credential="human-token")
    assert rec.cleared_authenticated is True
    assert rec.cleared_by == "ciso@bank.example"
    assert v.is_vetoed is False


def test_agent_principal_cannot_clear(authorizer: StubAuthorizer) -> None:
    v = SovereignVeto(agent_id="a", authorizer=authorizer, mode="production")
    v.trigger(VetoReason.MANUAL, "x", "y")
    with pytest.raises(VetoNotAuthorizedError, match="agent principal"):
        v.clear("ok", credential="agent-token")
    assert v.is_vetoed is True  # still vetoed


def test_bad_credential_rejected(authorizer: StubAuthorizer) -> None:
    v = SovereignVeto(agent_id="a", authorizer=authorizer, mode="production")
    v.trigger(VetoReason.MANUAL, "x", "y")
    with pytest.raises(VetoNotAuthorizedError, match="authentication"):
        v.clear("ok", credential="forged")


def test_authorizer_present_but_no_credential(authorizer: StubAuthorizer) -> None:
    v = SovereignVeto(agent_id="a", authorizer=authorizer)
    v.trigger(VetoReason.MANUAL, "x", "y")
    with pytest.raises(VetoNotAuthorizedError, match="credential is required"):
        v.clear("ok")


def test_unauthorized_action_rejected(restricted_authorizer: StubAuthorizer) -> None:
    v = SovereignVeto(agent_id="a", authorizer=restricted_authorizer, mode="production")
    v.trigger(VetoReason.MANUAL, "x", "y")
    with pytest.raises(VetoNotAuthorizedError, match="not authorized"):
        v.clear("ok", credential="human-token")


def test_clear_with_no_active_veto() -> None:
    v = SovereignVeto(agent_id="a")
    with pytest.raises(ValueError, match="no active veto"):
        v.clear("ok", operator_id="human")


def test_advisory_clear_requires_operator_id() -> None:
    v = SovereignVeto(agent_id="a")
    v.trigger(VetoReason.MANUAL, "x", "y")
    with pytest.raises(ValueError, match="operator_id is required"):
        v.clear("ok")


def test_trigger_and_clear_recorded_to_chain(authorizer: StubAuthorizer) -> None:
    chain = AuditChain(deployer_id="bank-x")
    v = SovereignVeto(agent_id="a", authorizer=authorizer, mode="production", audit_chain=chain)
    v.trigger(VetoReason.MODEL_DRIFT, "monitor", "psi high")
    v.clear("resolved", credential="human-token")
    types = [e.event_type.value for e in chain.events()]
    assert "veto_triggered" in types
    assert "veto_cleared" in types
    assert chain.verify() is True


def test_invalid_mode() -> None:
    with pytest.raises(ValueError, match="mode"):
        SovereignVeto(agent_id="a", mode="bogus")
