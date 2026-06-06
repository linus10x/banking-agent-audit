"""P1 — autonomy-ladder level-gate tests (corrected: independent attestation)."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from banking_agent_audit.governance.autonomy_ladder import (
    LEVEL_REQUIRED_CONTROLS,
    AutonomyLadder,
    ControlAttestation,
)
from banking_agent_audit.schemas.audit_event import AutonomyLevel
from tests.conftest import StubVerifier

A0 = AutonomyLevel.A0_INFORMATIONAL
A1 = AutonomyLevel.A1_ASSISTED
A2 = AutonomyLevel.A2_DELEGATED
A3 = AutonomyLevel.A3_SUPERVISED_AUTONOMOUS
A4 = AutonomyLevel.A4_PRODUCTION_AUTONOMOUS


def _atts(level_up_to: AutonomyLevel, attester: str = "validator") -> list[ControlAttestation]:
    """Attestations for every control required up to and including ``level_up_to``."""
    out: list[ControlAttestation] = []
    for level, controls in LEVEL_REQUIRED_CONTROLS.items():
        if level.rank <= level_up_to.rank:
            out.extend(
                ControlAttestation(c, level, attester, f"{c} in place", "sig") for c in controls
            )
    return out


def test_production_requires_verifier() -> None:
    with pytest.raises(ValueError, match="verifier"):
        AutonomyLadder(mode="production")


def test_refuses_promotion_with_missing_controls() -> None:
    gate = AutonomyLadder()
    d = gate.evaluate_promotion(
        requesting_agent_id="agent",
        current_level=A0,
        requested_level=A1,
        attestations=[],  # missing human_approval_workflow
    )
    assert d.approved is False
    assert "human_approval_workflow" in d.missing_controls
    assert d.granted_level == A0


def test_grants_one_rung_with_all_controls_advisory() -> None:
    gate = AutonomyLadder()
    d = gate.evaluate_promotion(
        requesting_agent_id="agent",
        current_level=A0,
        requested_level=A1,
        attestations=_atts(A1),
    )
    assert d.approved is True
    assert d.granted_level == A1
    assert d.verified is False  # advisory, labeled
    assert any("ADVISORY" in r for r in d.reasons)


def test_rung_skip_refused() -> None:
    gate = AutonomyLadder()
    d = gate.evaluate_promotion(
        requesting_agent_id="agent",
        current_level=A0,
        requested_level=A2,
        attestations=_atts(A2),
    )
    assert d.approved is False
    assert any("rung-skip" in r for r in d.reasons)


def test_rung_skip_allowed_when_opted_in() -> None:
    gate = AutonomyLadder(allow_skip=True)
    d = gate.evaluate_promotion(
        requesting_agent_id="agent",
        current_level=A0,
        requested_level=A2,
        attestations=_atts(A2),
    )
    assert d.approved is True
    assert d.granted_level == A2


def test_demotion_always_allowed() -> None:
    gate = AutonomyLadder()
    d = gate.evaluate_promotion(
        requesting_agent_id="agent",
        current_level=A3,
        requested_level=A1,
        attestations=[],
    )
    assert d.approved is True
    assert d.granted_level == A1


def test_production_rejects_self_attestation() -> None:
    # The agent attests its OWN controls; an independent verifier rejects them.
    verifier = StubVerifier(independent_attesters={"validator"})
    gate = AutonomyLadder(verifier=verifier, mode="production")
    self_atts = _atts(A1, attester="agent")  # attester == requesting agent
    d = gate.evaluate_promotion(
        requesting_agent_id="agent",
        current_level=A0,
        requested_level=A1,
        attestations=self_atts,
    )
    assert d.approved is False
    assert "human_approval_workflow" in d.unverified_controls


def test_production_accepts_independent_attestation() -> None:
    verifier = StubVerifier(independent_attesters={"validator"})
    gate = AutonomyLadder(verifier=verifier, mode="production")
    d = gate.evaluate_promotion(
        requesting_agent_id="agent",
        current_level=A0,
        requested_level=A1,
        attestations=_atts(A1, attester="validator"),
    )
    assert d.approved is True
    assert d.verified is True


def test_invalid_mode() -> None:
    with pytest.raises(ValueError, match="mode"):
        AutonomyLadder(mode="bogus")


@settings(max_examples=1500)
@given(
    cur=st.sampled_from(list(AutonomyLevel)),
    tgt=st.sampled_from(list(AutonomyLevel)),
)
def test_property_promotion_without_controls_never_grants_higher(
    cur: AutonomyLevel, tgt: AutonomyLevel
) -> None:
    gate = AutonomyLadder()
    d = gate.evaluate_promotion(
        requesting_agent_id="agent",
        current_level=cur,
        requested_level=tgt,
        attestations=[],
    )
    # A promotion that requires any new control cannot be granted with no
    # attestations: it must fall back to the current level.
    requires_new_control = any(
        controls for lvl, controls in LEVEL_REQUIRED_CONTROLS.items() if lvl.rank <= tgt.rank
    )
    if tgt.rank > cur.rank and requires_new_control:
        assert d.approved is False
        assert d.granted_level == cur
    else:
        assert d.granted_level.rank <= max(cur.rank, tgt.rank)
