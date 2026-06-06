"""P4 — DEFCON transition-direction guard tests."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from banking_agent_audit.governance.audit_chain import AuditChain
from banking_agent_audit.governance.defcon import (
    DEFCON,
    DEFCONMachine,
    DEFCONTransitionError,
    RiskMetrics,
)
from tests.conftest import StubAuthorizer


def test_production_requires_authorizer() -> None:
    with pytest.raises(ValueError, match="authorizer"):
        DEFCONMachine(mode="production")


def test_escalates_immediately_on_breach() -> None:
    m = DEFCONMachine()
    assert m.current_level() is DEFCON.NORMAL
    m.evaluate(RiskMetrics(portfolio_drawdown=0.25))  # HALT threshold
    assert m.current_level() is DEFCON.HALT


def test_evaluate_never_auto_deescalates() -> None:
    m = DEFCONMachine()
    m.evaluate(RiskMetrics(portfolio_drawdown=0.25))  # -> HALT
    m.evaluate(RiskMetrics(portfolio_drawdown=0.0))  # calm metrics
    assert m.current_level() is DEFCON.HALT  # stays HALT


def test_one_call_halt_to_normal_refused() -> None:
    m = DEFCONMachine()
    m.evaluate(RiskMetrics(portfolio_drawdown=0.25))  # -> HALT
    with pytest.raises(DEFCONTransitionError, match="one level at a time"):
        m.manual_override(DEFCON.NORMAL, "all clear", operator_id="human")
    assert m.current_level() is DEFCON.HALT


def test_one_step_deescalation_advisory() -> None:
    m = DEFCONMachine()
    m.evaluate(RiskMetrics(portfolio_drawdown=0.25))  # HALT
    m.manual_override(DEFCON.DANGER, "stabilizing", operator_id="human")
    assert m.current_level() is DEFCON.DANGER


def test_deescalation_requires_authorized_human(authorizer: StubAuthorizer) -> None:
    m = DEFCONMachine(authorizer=authorizer, mode="production")
    m.evaluate(RiskMetrics(daily_loss=0.12))  # HALT
    # agent principal refused
    with pytest.raises(DEFCONTransitionError, match="agent principal"):
        m.manual_override(DEFCON.DANGER, "x", credential="agent-token")
    # bad credential refused
    with pytest.raises(DEFCONTransitionError, match="authentication"):
        m.manual_override(DEFCON.DANGER, "x", credential="forged")
    # authenticated human ok
    m.manual_override(DEFCON.DANGER, "x", credential="human-token")
    assert m.current_level() is DEFCON.DANGER


def test_deescalation_requires_credential_when_authorizer(authorizer: StubAuthorizer) -> None:
    m = DEFCONMachine(authorizer=authorizer, mode="production")
    m.evaluate(RiskMetrics(daily_loss=0.12))
    with pytest.raises(DEFCONTransitionError, match="credential is required"):
        m.manual_override(DEFCON.DANGER, "x")


def test_unauthorized_human_refused(restricted_authorizer: StubAuthorizer) -> None:
    m = DEFCONMachine(authorizer=restricted_authorizer, mode="production")
    m.evaluate(RiskMetrics(daily_loss=0.12))
    with pytest.raises(DEFCONTransitionError, match="not authorized"):
        m.manual_override(DEFCON.DANGER, "x", credential="human-token")


def test_manual_escalation_allowed() -> None:
    m = DEFCONMachine()
    m.manual_override(DEFCON.ALERT, "preemptive", operator_id="human")
    assert m.current_level() is DEFCON.ALERT


def test_noop_override_returns_current() -> None:
    m = DEFCONMachine()
    assert m.manual_override(DEFCON.NORMAL, "noop") is DEFCON.NORMAL


def test_advisory_deescalation_requires_operator() -> None:
    m = DEFCONMachine()
    m.evaluate(RiskMetrics(portfolio_drawdown=0.25))
    with pytest.raises(DEFCONTransitionError, match="operator_id required"):
        m.manual_override(DEFCON.DANGER, "x")


def test_transitions_recorded(authorizer: StubAuthorizer) -> None:
    chain = AuditChain(deployer_id="bank-x")
    m = DEFCONMachine(authorizer=authorizer, mode="production", audit_chain=chain)
    m.evaluate(RiskMetrics(portfolio_drawdown=0.25))
    m.manual_override(DEFCON.DANGER, "x", credential="human-token")
    types = [e.event_type.value for e in chain.events()]
    assert types.count("defcon_transition") == 2
    assert chain.verify() is True


@settings(max_examples=2000, deadline=None)
@given(
    dd=st.floats(min_value=0.0, max_value=1.0),
    dl=st.floats(min_value=0.0, max_value=1.0),
    cl=st.integers(min_value=0, max_value=20),
)
def test_property_evaluate_is_monotonic_nondecreasing(dd: float, dl: float, cl: int) -> None:
    m = DEFCONMachine()
    prev = m.current_level()
    for _ in range(3):
        lvl = m.evaluate(RiskMetrics(portfolio_drawdown=dd, daily_loss=dl, consecutive_losses=cl))
        assert lvl >= prev  # evaluate() can only escalate or hold
        prev = lvl


@settings(max_examples=1500)
@given(target=st.sampled_from([DEFCON.NORMAL, DEFCON.CAUTION, DEFCON.ALERT, DEFCON.DANGER]))
def test_property_no_multistep_deescalation_from_halt(target: DEFCON) -> None:
    m = DEFCONMachine()
    m.evaluate(RiskMetrics(portfolio_drawdown=0.25))  # HALT
    if DEFCON.HALT - target > 1:
        with pytest.raises(DEFCONTransitionError):
            m.manual_override(target, "x", operator_id="human")
