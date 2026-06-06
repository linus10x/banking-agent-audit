"""Banking control — ECOA/Reg B §1002.9 adverse-action gate."""

from __future__ import annotations

from banking_agent_audit.governance.adverse_action_gate import (
    AdverseActionDecision,
    AdverseActionGate,
    AdverseActionType,
)
from banking_agent_audit.governance.audit_chain import AuditChain


def _decision(**kw) -> AdverseActionDecision:
    base = dict(
        applicant_id="app-1",
        action_type=AdverseActionType.DENIAL,
        principal_reasons=("debt-to-income ratio 0.62 exceeds 0.43 product limit",),
        notice_provided=True,
        days_to_notice=10,
        used_consumer_report=False,
    )
    base.update(kw)
    return AdverseActionDecision(**base)  # type: ignore[arg-type]


def test_compliant_specific_reason() -> None:
    res = AdverseActionGate().evaluate(_decision())
    assert res.compliant is True
    assert res.violations == ()
    assert "12 CFR §1002.9" in res.citations


def test_no_notice_is_violation() -> None:
    res = AdverseActionGate().evaluate(_decision(notice_provided=False))
    assert res.compliant is False
    assert any("notification" in v for v in res.violations)


def test_late_notice_is_violation() -> None:
    res = AdverseActionGate().evaluate(_decision(days_to_notice=45))
    assert res.compliant is False
    assert any("window" in v for v in res.violations)


def test_no_reasons_is_violation() -> None:
    res = AdverseActionGate().evaluate(_decision(principal_reasons=()))
    assert res.compliant is False
    assert any("specific reasons" in v for v in res.violations)


def test_generic_reason_warns_not_blocks() -> None:
    res = AdverseActionGate().evaluate(_decision(principal_reasons=("internal policy",)))
    # Generic reason is a warning (human review), not an automatic violation —
    # the gate does not certify reason sufficiency, it flags likely problems.
    assert res.compliant is True
    assert any("generic" in w for w in res.warnings)


def test_blank_reason_is_violation() -> None:
    # A blank/whitespace reason is no reason — a violation, not just a warning.
    res = AdverseActionGate().evaluate(_decision(principal_reasons=("   ",)))
    assert res.compliant is False
    assert any("blank" in v for v in res.violations)


def test_negative_days_to_notice_is_violation() -> None:
    res = AdverseActionGate().evaluate(_decision(days_to_notice=-5))
    assert res.compliant is False
    assert any("negative" in v for v in res.violations)


def test_fullwidth_generic_reason_still_flagged() -> None:
    # NFKC folds fullwidth compatibility variants, so "ｏther" is still caught.
    res = AdverseActionGate().evaluate(_decision(principal_reasons=("ｏther",)))
    assert any("generic" in w for w in res.warnings)


def test_fcra_overlay_requires_disclosures() -> None:
    res = AdverseActionGate().evaluate(
        _decision(used_consumer_report=True)  # all FCRA flags default False
    )
    assert res.compliant is False
    joined = " ".join(res.violations)
    assert "CRA name" in joined
    assert "credit score" in joined
    assert "applicant rights" in joined
    assert "15 U.S.C. §1681m (FCRA §615)" in res.citations


def test_fcra_overlay_satisfied() -> None:
    res = AdverseActionGate().evaluate(
        _decision(
            used_consumer_report=True,
            cra_name_provided=True,
            credit_score_disclosed=True,
            applicant_rights_disclosed=True,
        )
    )
    assert res.compliant is True


def test_configurable_deadline() -> None:
    gate = AdverseActionGate(notice_deadline_days=15)
    assert gate.evaluate(_decision(days_to_notice=20)).compliant is False
    assert gate.evaluate(_decision(days_to_notice=12)).compliant is True


def test_records_to_chain() -> None:
    chain = AuditChain(deployer_id="bank-x")
    AdverseActionGate(audit_chain=chain).evaluate(_decision())
    assert chain.events()[-1].event_type.value == "adverse_action"
    assert chain.verify() is True
