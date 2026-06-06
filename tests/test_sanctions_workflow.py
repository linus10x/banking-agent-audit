"""OFAC / sanctions reference disposition-workflow tests."""

from __future__ import annotations

from typing import Any

import pytest

from banking_agent_audit.governance.audit_chain import AuditChain
from banking_agent_audit.governance.sanctions_workflow import (
    DispositionState,
    SanctionsDispositionWorkflow,
    ScreeningMatch,
    UnwiredListProvider,
)
from banking_agent_audit.governance.sovereign_veto import SovereignVeto


class StubListProvider:
    """A test list provider that matches one specific name (NOT a real list)."""

    source = "test-stub-list"

    def __init__(self, hit_name: str, score: float = 0.95) -> None:
        self._hit = hit_name
        self._score = score

    def screen(self, subject_name: str, context: dict[str, Any]) -> list[ScreeningMatch]:
        if subject_name == self._hit:
            return [ScreeningMatch(self._hit, self._score, self.source, {"program": "TEST"})]
        return []


def test_default_provider_is_unwired() -> None:
    wf = SanctionsDispositionWorkflow()
    assert wf.provider_is_unwired is True
    assert wf.list_source == "UNWIRED-BY-DEPLOYER"


def test_no_bundled_list_clears_but_flags_unwired() -> None:
    wf = SanctionsDispositionWorkflow()
    case = wf.screen_and_dispose("cust-1", "Anyone At All")
    assert case.state is DispositionState.CLEARED
    assert case.provider_unwired is True  # honest: nothing was actually screened


def test_unwired_provider_returns_no_matches() -> None:
    assert UnwiredListProvider().screen("x", {}) == []


def test_clean_subject_clears() -> None:
    wf = SanctionsDispositionWorkflow(list_provider=StubListProvider("BAD ACTOR"))
    case = wf.screen_and_dispose("cust-1", "Good Customer")
    assert case.state is DispositionState.CLEARED


def test_match_escalates_then_blocks_and_vetoes() -> None:
    veto = SovereignVeto(agent_id="payment-agent")
    wf = SanctionsDispositionWorkflow(
        list_provider=StubListProvider("BAD ACTOR"),
        sovereign_veto=veto,
    )
    case = wf.screen_and_dispose("cust-9", "BAD ACTOR")
    assert case.state is DispositionState.ESCALATED
    assert len(case.matches) == 1
    resolved = wf.resolve_case(case.case_id, true_positive=True, reviewer_id="aml-officer")
    assert resolved.state is DispositionState.BLOCKED
    assert veto.is_vetoed is True  # veto fired on confirmed hit


def test_false_positive_clears_no_veto() -> None:
    veto = SovereignVeto(agent_id="payment-agent")
    wf = SanctionsDispositionWorkflow(
        list_provider=StubListProvider("BAD ACTOR"),
        sovereign_veto=veto,
    )
    case = wf.screen_and_dispose("cust-9", "BAD ACTOR")
    resolved = wf.resolve_case(case.case_id, true_positive=False, reviewer_id="aml-officer")
    assert resolved.state is DispositionState.FALSE_POSITIVE_CLEARED
    assert veto.is_vetoed is False


def test_below_threshold_does_not_open_case() -> None:
    wf = SanctionsDispositionWorkflow(
        list_provider=StubListProvider("BAD ACTOR", score=0.4),
        match_threshold=0.85,
    )
    case = wf.screen_and_dispose("cust-9", "BAD ACTOR")
    assert case.state is DispositionState.CLEARED
    assert case.matches == ()


def test_resolve_cleared_case_raises() -> None:
    wf = SanctionsDispositionWorkflow(list_provider=StubListProvider("BAD ACTOR"))
    case = wf.screen_and_dispose("cust-1", "Good Customer")  # CLEARED
    with pytest.raises(ValueError, match="nothing to resolve"):
        wf.resolve_case(case.case_id, true_positive=True, reviewer_id="x")


def test_full_disposition_trail_recorded() -> None:
    chain = AuditChain(deployer_id="bank-x")
    wf = SanctionsDispositionWorkflow(
        list_provider=StubListProvider("BAD ACTOR"),
        audit_chain=chain,
    )
    case = wf.screen_and_dispose("cust-9", "BAD ACTOR")
    wf.resolve_case(case.case_id, true_positive=True, reviewer_id="aml-officer")
    types = [e.event_type.value for e in chain.events()]
    assert "sanctions_screening" in types
    assert "sanctions_hold" in types
    assert "sanctions_escalation" in types
    assert "sanctions_disposition" in types
    assert chain.verify() is True


def test_case_history_tracks_states() -> None:
    wf = SanctionsDispositionWorkflow(list_provider=StubListProvider("BAD ACTOR"))
    case = wf.screen_and_dispose("cust-9", "BAD ACTOR")
    actions = [h["action"] for h in case.history]
    assert "hold_opened" in actions
    assert "escalated_for_review" in actions
    assert wf.get(case.case_id) is case
