"""Banking control — Model Risk Management with genuine effective-challenge.

A 0.1.0 MUST-HAVE control. It is a thin, *real* governance layer over the P5
:class:`~.effective_challenge_harness.EffectiveChallengeHarness`: a model
inventory whose validation status is **gated on attested challenger
independence**. A model whose challenge ran without established independence
cannot reach ``APPROVED`` — it is forced to ``ESCALATED``. This encodes the
load-bearing concept of effective challenge: a primary model owner cannot
self-validate.

Regulatory framing (honest claim layer): "effective challenge" originates in
SR 11-7 (Federal Reserve / OCC 2011-12), **rescinded 2026-04-17** and
superseded by the 2026 revised interagency Model Risk Management guidance
(OCC Bulletin 2026-13), which carries the model-validation principle forward
while stating that generative and agentic AI models "are not within the scope
of this guidance." This module is a *documented reference control*, not a
deployed bank MRM system. See ``docs/regulatory/model_risk_mrm_mapping.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

from banking_agent_audit.governance.audit_chain import AuditChain
from banking_agent_audit.governance.effective_challenge_harness import (
    ChallengeReport,
    Recommendation,
)
from banking_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class ModelRiskTier(Enum):
    """Materiality tier driving validation cadence and challenge rigor."""

    TIER_1_HIGH = "tier_1_high"
    TIER_2_MEDIUM = "tier_2_medium"
    TIER_3_LOW = "tier_3_low"


class ValidationStatus(Enum):
    NOT_VALIDATED = "not_validated"
    APPROVED = "approved"
    CONDITIONAL = "conditional"
    ESCALATED = "escalated"


@dataclass
class ModelRecord:
    model_id: str
    owner: str
    purpose: str
    risk_tier: ModelRiskTier
    status: ValidationStatus = ValidationStatus.NOT_VALIDATED
    last_validated_at: str | None = None
    last_challenger_id: str | None = None
    last_recommendation: str | None = None
    independence_established: bool = False


class ModelRiskManagement:
    """A model inventory whose validation status is gated on real independence."""

    def __init__(
        self,
        *,
        audit_chain: AuditChain | None = None,
    ) -> None:
        self._chain = audit_chain
        self._models: dict[str, ModelRecord] = {}

    def register(
        self,
        model_id: str,
        *,
        owner: str,
        purpose: str,
        risk_tier: ModelRiskTier,
    ) -> ModelRecord:
        """Add a model to the inventory (idempotent on ``model_id``)."""
        if model_id in self._models:
            raise ValueError(f"model {model_id!r} already registered")
        record = ModelRecord(model_id=model_id, owner=owner, purpose=purpose, risk_tier=risk_tier)
        self._models[model_id] = record
        return record

    def get(self, model_id: str) -> ModelRecord:
        return self._models[model_id]

    def record_validation(self, model_id: str, report: ChallengeReport) -> ValidationStatus:
        """Apply an effective-challenge report to a model's validation status.

        ``APPROVED`` requires BOTH attested independence AND an
        ``ACCEPT_PRIMARY`` recommendation. Without independence the model is
        forced to ``ESCALATED`` — a primary owner cannot self-validate.

        The report must be the one produced for this model: ``report.primary_id``
        must match ``model_id``. Otherwise a clean report for an easy model could
        be replayed to mark a different, un-challenged model APPROVED.
        """
        if report.primary_id != model_id:
            raise ValueError(
                f"report.primary_id {report.primary_id!r} does not match model_id "
                f"{model_id!r}; a report may only validate the model it challenged"
            )
        record = self._models[model_id]
        if not report.independent:
            status = ValidationStatus.ESCALATED
        elif report.recommendation is Recommendation.ACCEPT_PRIMARY:
            status = ValidationStatus.APPROVED
        elif report.recommendation is Recommendation.INVESTIGATE:
            status = ValidationStatus.CONDITIONAL
        else:
            status = ValidationStatus.ESCALATED

        record.status = status
        record.last_validated_at = _now_iso()
        record.last_challenger_id = report.challenger_id
        record.last_recommendation = report.recommendation.value
        record.independence_established = report.independent

        if self._chain is not None:
            self._chain.append(
                AuditEventType.MODEL_VALIDATED,
                AutonomyLevel.A0_INFORMATIONAL,
                agent_id=model_id,
                payload={
                    "status": status.value,
                    "independent": report.independent,
                    "recommendation": report.recommendation.value,
                    "challenger_id": report.challenger_id,
                    "risk_tier": record.risk_tier.value,
                },
                actor_id=record.owner,
            )
        return status

    def approved_models(self) -> list[str]:
        return [m.model_id for m in self._models.values() if m.status is ValidationStatus.APPROVED]

    def independence_gaps(self) -> list[str]:
        """Models that are not independently validated (audit-finding surface)."""
        return [m.model_id for m in self._models.values() if not m.independence_established]
