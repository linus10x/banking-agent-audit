"""Banking control — ECOA / Regulation B §1002.9 adverse-action gate.

A 0.1.0 MUST-HAVE control. It enforces the *structure* of an adverse-action
notice when an AI/model-driven credit decision denies, revokes, or worsens
terms — timing, the statement of **specific** principal reasons, and the FCRA
§615 overlay when a consumer report drove the decision.

Reg-citation discipline (hard gate): this module **does not author a
Regulation B reason-code enumeration from memory.** Regulation B requires a
statement of the *specific* principal reasons for the action
(12 CFR §1002.9(b)(2)); the sample reasons in Appendix C to Part 1002 are
illustrative, and the CFPB has stated (Circular 2022-03) that a creditor may
not rely on generic or checklist reasons that do not reflect the actual basis
of the decision, including for complex algorithmic models. So the gate
**validates that deployer-supplied reasons are specific** rather than asserting
an authoritative code list. Any fixed sample taxonomy is marked ``UNVERIFIED``
and routed to the Reg B appendix / counsel.

Primary sources (verify against these — see ``docs/regulatory/ecoa_reg_b_mapping.md``):
* ECOA / Reg B §1002.9 (12 CFR §1002.9) — CFPB:
  https://www.consumerfinance.gov/rules-policy/regulations/1002/9/
* FCRA §615 (15 U.S.C. §1681m) — adverse-action notices on consumer-report use:
  https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act
* CFPB Circular 2022-03 — specific, accurate reasons required for complex models.

UNVERIFIED: the precise notice-timing window and its exceptions
(§1002.9(a)(1) and related) must be confirmed against the regulation text for a
given creditor's facts; the default below is a configurable parameter, not a
legal determination.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from enum import Enum

from banking_agent_audit.governance.audit_chain import AuditChain
from banking_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel

# Heuristic aid only — phrases that are too generic to be a "specific reason"
# under §1002.9(b)(2) per CFPB Circular 2022-03. NOT an authoritative list; it
# flags likely-insufficient reasons for human review, it does not certify
# sufficiency. Deployers tune this for their products.
_GENERIC_REASON_MARKERS: tuple[str, ...] = (
    "internal policy",
    "other",
    "score too low",
    "credit scoring system",
    "did not meet criteria",
    "does not meet our standards",
    "proprietary model",
    "n/a",
)


class AdverseActionType(Enum):
    """The kinds of action that trigger ECOA/Reg B notice obligations."""

    DENIAL = "denial"
    REVOCATION = "revocation"
    UNFAVORABLE_CHANGE = "unfavorable_change_in_terms"
    COUNTEROFFER_NOT_ACCEPTED = "counteroffer_not_accepted"


@dataclass(frozen=True)
class AdverseActionDecision:
    """The decision under review and the deployer-supplied notice content."""

    applicant_id: str
    action_type: AdverseActionType
    principal_reasons: tuple[str, ...]
    notice_provided: bool
    days_to_notice: int
    used_consumer_report: bool = False
    # FCRA §615 overlay fields (required when used_consumer_report is True):
    cra_name_provided: bool = False
    credit_score_disclosed: bool = False
    applicant_rights_disclosed: bool = False


@dataclass(frozen=True)
class NoticeComplianceResult:
    applicant_id: str
    compliant: bool
    violations: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    citations: tuple[str, ...] = field(default_factory=tuple)


class AdverseActionGate:
    """Validate an adverse-action notice against ECOA/Reg B §1002.9 (+ FCRA §615).

    Parameters
    ----------
    notice_deadline_days:
        Configurable notice window (default 30; confirm against §1002.9(a)(1)
        for the creditor's facts — see module UNVERIFIED note).
    audit_chain:
        Optional chain; each evaluation is recorded when wired.
    """

    def __init__(
        self,
        *,
        notice_deadline_days: int = 30,
        audit_chain: AuditChain | None = None,
    ) -> None:
        self._deadline = notice_deadline_days
        self._chain = audit_chain

    def evaluate(self, decision: AdverseActionDecision) -> NoticeComplianceResult:
        """Return a structured compliance result for one adverse-action decision."""
        violations: list[str] = []
        warnings: list[str] = []
        citations: list[str] = ["12 CFR §1002.9"]

        # (1) Notice must be provided.
        if not decision.notice_provided:
            violations.append(
                "no adverse-action notice provided (§1002.9(a) requires notification)"
            )

        # (2) Timing.
        if decision.days_to_notice < 0:
            violations.append(
                f"days_to_notice is negative ({decision.days_to_notice}); a notice cannot "
                "precede the action it reports"
            )
        elif decision.notice_provided and decision.days_to_notice > self._deadline:
            violations.append(
                f"notice provided {decision.days_to_notice} days after action; "
                f"exceeds the {self._deadline}-day window (§1002.9(a)(1))"
            )

        # (3) Specific principal reasons (§1002.9(b)(2)).
        if not decision.principal_reasons:
            violations.append(
                "no specific principal reasons stated (§1002.9(b)(2) requires "
                "a statement of specific reasons)"
            )
        else:
            for reason in decision.principal_reasons:
                if not reason.strip():
                    # A blank reason is no reason — a violation, not a warning.
                    violations.append(
                        "a stated principal reason is blank (§1002.9(b)(2) requires "
                        "specific reasons)"
                    )
                elif self._is_generic(reason):
                    warnings.append(
                        f"reason {reason!r} appears generic; §1002.9(b)(2) + CFPB "
                        "Circular 2022-03 require specific, accurate reasons "
                        "(verify against the actual decision basis)"
                    )

        # (4) FCRA §615 overlay when a consumer report drove the decision.
        if decision.used_consumer_report:
            citations.append("15 U.S.C. §1681m (FCRA §615)")
            if not decision.cra_name_provided:
                violations.append(
                    "consumer report used but CRA name/address/phone not disclosed "
                    "(FCRA §615(a)(3))"
                )
            if not decision.credit_score_disclosed:
                violations.append(
                    "consumer report used but credit score + key factors not disclosed "
                    "(FCRA §615(a)(2), incorporating the §609(f) / 15 U.S.C. §1681g(f) score "
                    "disclosure; separate risk-based-pricing path at §615(h) / Reg V, "
                    "12 CFR Part 1022 subpart H)"
                )
            if not decision.applicant_rights_disclosed:
                violations.append(
                    "consumer report used but applicant rights (free report, dispute) "
                    "not disclosed (FCRA §615(a)(4))"
                )

        compliant = not violations
        result = NoticeComplianceResult(
            applicant_id=decision.applicant_id,
            compliant=compliant,
            violations=tuple(violations),
            warnings=tuple(warnings),
            citations=tuple(citations),
        )
        self._record(decision, result)
        return result

    @staticmethod
    def _is_generic(reason: str) -> bool:
        # NFKC-normalize so Unicode compatibility variants (e.g. fullwidth forms)
        # do not slip past the heuristic markers. This is a non-authoritative
        # warning aid, not a confusables/homoglyph detector. (Blank reasons are
        # handled as violations upstream.)
        low = unicodedata.normalize("NFKC", reason).strip().casefold()
        if not low:
            return False
        return any(marker in low for marker in _GENERIC_REASON_MARKERS)

    def _record(self, decision: AdverseActionDecision, result: NoticeComplianceResult) -> None:
        if self._chain is None:
            return
        self._chain.append(
            AuditEventType.ADVERSE_ACTION,
            AutonomyLevel.A0_INFORMATIONAL,
            agent_id="banking-adverse-action-gate",
            payload={
                "applicant_id": decision.applicant_id,
                "action_type": decision.action_type.value,
                "compliant": result.compliant,
                "violation_count": len(result.violations),
                "used_consumer_report": decision.used_consumer_report,
            },
            actor_id="banking-adverse-action-gate",
        )
