"""Banking control — Model Risk Management (effective-challenge gating)."""

from __future__ import annotations

import pytest

from banking_agent_audit.governance.audit_chain import AuditChain
from banking_agent_audit.governance.effective_challenge_harness import (
    EffectiveChallengeHarness,
    IndependenceAttestation,
)
from banking_agent_audit.governance.model_risk_management import (
    ModelRiskManagement,
    ModelRiskTier,
    ValidationStatus,
)


def _report(*, independent: bool, agree: bool):
    att = IndependenceAttestation(
        chosen_by="mrm",
        same_owner=not independent,
        same_vendor_family=not independent,
        same_prompt_template=not independent,
    )
    challenger = (lambda x: x) if agree else (lambda x: -x)
    return EffectiveChallengeHarness(
        primary_model=lambda x: x,
        challenger_model=challenger,
        eval_set=[(1, 1), (2, 2)],
        independence=att,
        primary_id="m1",
        challenger_id="m2",
    ).run()


def _mrm() -> ModelRiskManagement:
    m = ModelRiskManagement()
    m.register("m1", owner="quant-desk", purpose="pd-model", risk_tier=ModelRiskTier.TIER_1_HIGH)
    return m


def test_independent_agreement_approves() -> None:
    m = _mrm()
    status = m.record_validation("m1", _report(independent=True, agree=True))
    assert status is ValidationStatus.APPROVED
    assert "m1" in m.approved_models()
    assert m.independence_gaps() == []


def test_no_independence_escalates_even_on_agreement() -> None:
    m = _mrm()
    status = m.record_validation("m1", _report(independent=False, agree=True))
    assert status is ValidationStatus.ESCALATED
    assert m.approved_models() == []
    assert "m1" in m.independence_gaps()


def test_disagreement_escalates() -> None:
    m = _mrm()
    status = m.record_validation("m1", _report(independent=True, agree=False))
    assert status is ValidationStatus.ESCALATED


def test_duplicate_register_rejected() -> None:
    m = _mrm()
    with pytest.raises(ValueError, match="already registered"):
        m.register("m1", owner="x", purpose="y", risk_tier=ModelRiskTier.TIER_3_LOW)


def test_records_to_chain() -> None:
    chain = AuditChain(deployer_id="bank-x")
    m = ModelRiskManagement(audit_chain=chain)
    m.register("m1", owner="quant", purpose="pd", risk_tier=ModelRiskTier.TIER_2_MEDIUM)
    m.record_validation("m1", _report(independent=True, agree=True))
    assert chain.events()[-1].event_type.value == "model_validated"
    assert chain.verify() is True


def test_get_returns_record() -> None:
    m = _mrm()
    rec = m.get("m1")
    assert rec.owner == "quant-desk"
    assert rec.status is ValidationStatus.NOT_VALIDATED
