"""Golden-corpus tests — assert the library GOVERNS each real matter's category.

For every verified, public enforcement action in ``corpus.CORPUS`` we assert:

1. fixture integrity (primary-source URL + citation + verified flag), and
2. that the control named in ``which_control`` would have *governed or flagged*
   the category the matter falls into — demonstrated by running a representative
   (synthetic, non-fact-asserting) scenario through that control.

We never assert facts about the real case beyond its public matter of record;
the synthetic scenario is modeled on the *category*, not the parties.
"""

from __future__ import annotations

import pytest

from banking_agent_audit import obligation_map as om
from banking_agent_audit.governance.adverse_action_gate import (
    AdverseActionDecision,
    AdverseActionGate,
    AdverseActionType,
)
from banking_agent_audit.governance.effective_challenge_harness import (
    EffectiveChallengeHarness,
    IndependenceAttestation,
)
from banking_agent_audit.governance.model_risk_management import (
    ModelRiskManagement,
    ModelRiskTier,
    ValidationStatus,
)
from banking_agent_audit.governance.sanctions_workflow import (
    DispositionState,
    SanctionsDispositionWorkflow,
    ScreeningMatch,
)
from banking_agent_audit.governance.sovereign_veto import SovereignVeto
from tests.golden.corpus import CORPUS, GoldenCase

KNOWN_CONTROLS = {
    "adverse_action_gate",
    "model_risk_management",
    "sanctions_workflow",
    "fair_lending_pattern",
}

_IDS = [c.case_id for c in CORPUS]


@pytest.mark.golden
@pytest.mark.parametrize("case", CORPUS, ids=_IDS)
def test_fixture_integrity(case: GoldenCase) -> None:
    assert case.primary_source_url.startswith("https://"), case.case_id
    assert case.citation.strip(), case.case_id
    assert case.which_control in KNOWN_CONTROLS, case.which_control
    assert isinstance(case.verified, bool)
    # Every case in the committed corpus is a verified matter of record.
    assert case.verified is True, f"{case.case_id} is not primary-source verified"


@pytest.mark.golden
def test_corpus_covers_all_four_categories() -> None:
    controls = {c.which_control for c in CORPUS}
    assert controls == KNOWN_CONTROLS  # all four governance surfaces represented


@pytest.mark.golden
def test_corpus_has_at_least_one_depository_bank_per_control() -> None:
    by_control: dict[str, bool] = {}
    for c in CORPUS:
        by_control[c.which_control] = by_control.get(c.which_control, False) or c.is_depository_bank
    for control, has_bank in by_control.items():
        assert has_bank, f"no depository-bank matter of record for {control}"


# --- governance demonstrations: the control flags the category's failure ---


class _StubListProvider:
    source = "golden-test-stub"

    def screen(self, subject_name: str, context: dict[str, object]) -> list[ScreeningMatch]:
        if subject_name == "SANCTIONED PARTY":
            return [ScreeningMatch("SANCTIONED PARTY", 0.97, self.source, {})]
        return []


@pytest.mark.golden
@pytest.mark.parametrize("case", CORPUS, ids=_IDS)
def test_control_governs_category(case: GoldenCase) -> None:
    if case.which_control == "adverse_action_gate":
        # An ECOA/Reg B failure analog: denial with no specific reasons + no FCRA
        # disclosures — the gate flags it as non-compliant.
        res = AdverseActionGate().evaluate(
            AdverseActionDecision(
                applicant_id="synthetic",
                action_type=AdverseActionType.DENIAL,
                principal_reasons=(),  # missing specific reasons
                notice_provided=True,
                days_to_notice=10,
                used_consumer_report=True,  # FCRA overlay unmet
            )
        )
        assert res.compliant is False
        assert any("specific reasons" in v for v in res.violations)

    elif case.which_control == "sanctions_workflow":
        veto = SovereignVeto(agent_id="payments-agent")
        wf = SanctionsDispositionWorkflow(list_provider=_StubListProvider(), sovereign_veto=veto)
        opened = wf.screen_and_dispose("subj", "SANCTIONED PARTY")
        assert opened.state is DispositionState.ESCALATED
        resolved = wf.resolve_case(opened.case_id, true_positive=True, reviewer_id="aml")
        assert resolved.state is DispositionState.BLOCKED
        assert veto.is_vetoed is True

    elif case.which_control == "model_risk_management":
        # An un-independently-validated algorithmic credit model cannot be APPROVED.
        mrm = ModelRiskManagement()
        mrm.register(
            "m", owner="quant", purpose="credit-underwriting", risk_tier=ModelRiskTier.TIER_1_HIGH
        )
        report = EffectiveChallengeHarness(
            primary_model=lambda x: x,
            challenger_model=lambda x: x,
            eval_set=[(1, 1), (2, 2)],
            independence=IndependenceAttestation(
                chosen_by="model-owner",
                same_owner=True,
                same_vendor_family=False,
                same_prompt_template=False,
            ),
            primary_id="m",
            challenger_id="challenger",
        ).run()
        assert mrm.record_validation("m", report) is ValidationStatus.ESCALATED

    elif case.which_control == "fair_lending_pattern":
        # Redlining/disparate-impact is governed as a DOCUMENTED PATTERN (honest
        # claim layer) — assert the obligation map carries a fair-lending entry.
        pattern_ids = {o.obligation_id for o in om.documented_patterns()} | {
            o.obligation_id for o in om.OBLIGATIONS
        }
        assert any("hmda" in pid or "avm" in pid or "tila" in pid for pid in pattern_ids), (
            "no fair-lending documented pattern in the obligation map"
        )
