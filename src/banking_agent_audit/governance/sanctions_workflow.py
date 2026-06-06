"""Banking pattern — OFAC / sanctions disposition WORKFLOW (reference only).

CLAIM LAYER (read carefully): this is a **reference disposition-workflow
pattern**, NOT an operating OFAC sanctions-screening control. It ships **no
bundled sanctions list**. Matching against an actual list is performed by a
deployer-wired :class:`SanctionsListProvider`; the default provider is
:class:`UnwiredListProvider`, whose source is labeled ``UNWIRED-BY-DEPLOYER`` and
which returns no matches because no list is wired. The value here is the
**screen → hold → escalate → veto** disposition state machine and its audit
trail, not sanctions data.

A confirmed true-positive disposition is a human act; when wired to a
:class:`~.sovereign_veto.SovereignVeto` in production mode it fires the veto
through the same authenticated path as any other veto.

Regulatory framing (honest): OFAC sanctions authority derives from IEEPA /
TWEA and the OFAC regulations (31 CFR Chapter V); the BSA AML-program and
suspicious-activity-reporting mandates are 31 U.S.C. §5318(h) and §5318(g)
respectively (umbrella: 31 U.S.C. §5311 et seq.; 31 CFR Chapter X, FinCEN).
This module references those regimes; it does **not** implement screening
against any sanctions list, nor the transaction-monitoring / SAR surface — only
a disposition workflow. See ``docs/regulatory/bsa_aml_ofac_mapping.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from banking_agent_audit.governance.audit_chain import AuditChain
from banking_agent_audit.governance.sovereign_veto import Authorizer, SovereignVeto, VetoReason
from banking_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel


class SanctionsNotAuthorizedError(PermissionError):
    """Raised when a case-resolution attempt fails authentication/authorization."""


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class DispositionState(Enum):
    CLEARED = "cleared"
    ON_HOLD = "on_hold"
    ESCALATED = "escalated"
    BLOCKED = "blocked"
    FALSE_POSITIVE_CLEARED = "false_positive_cleared"


@dataclass(frozen=True)
class ScreeningMatch:
    """A potential match returned by a wired list provider."""

    matched_name: str
    score: float
    list_source: str
    details: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class SanctionsListProvider(Protocol):
    """The pluggable list-source seam — UNWIRED-BY-DEPLOYER by default.

    A deployer wires a real provider (OFAC SDN, an internal watchlist, a
    vendor feed). ``source`` labels the list; ``screen`` returns candidate
    matches. This library bundles NO list.
    """

    @property
    def source(self) -> str: ...

    def screen(self, subject_name: str, context: dict[str, Any]) -> list[ScreeningMatch]: ...


class UnwiredListProvider:
    """Default provider — ships no list; source labeled ``UNWIRED-BY-DEPLOYER``.

    Returns no matches. The workflow records that screening ran against an
    unwired provider, so a deployment that forgets to wire a real list cannot
    silently appear to "pass" sanctions screening.
    """

    source = "UNWIRED-BY-DEPLOYER"

    def screen(self, subject_name: str, context: dict[str, Any]) -> list[ScreeningMatch]:
        return []


@dataclass
class DispositionCase:
    case_id: str
    subject_id: str
    subject_name: str
    state: DispositionState
    list_source: str
    matches: tuple[ScreeningMatch, ...] = ()
    history: list[dict[str, Any]] = field(default_factory=list)
    provider_unwired: bool = False


class SanctionsDispositionWorkflow:
    """The screen → hold → escalate → veto disposition state machine.

    Parameters
    ----------
    list_provider:
        Deployer-wired provider; defaults to :class:`UnwiredListProvider`.
    sovereign_veto:
        Optional veto fired on a confirmed true-positive.
    match_threshold:
        Score at/above which a match opens a hold.
    """

    RESOLVE_ACTION = "resolve_sanctions_case"

    def __init__(
        self,
        *,
        list_provider: SanctionsListProvider | None = None,
        sovereign_veto: SovereignVeto | None = None,
        authorizer: Authorizer | None = None,
        match_threshold: float = 0.85,
        audit_chain: AuditChain | None = None,
    ) -> None:
        self._provider: SanctionsListProvider = list_provider or UnwiredListProvider()
        self._veto = sovereign_veto
        self._authorizer = authorizer
        self._threshold = match_threshold
        self._chain = audit_chain
        self._cases: dict[str, DispositionCase] = {}
        self._counter = 0

    @property
    def list_source(self) -> str:
        return self._provider.source

    @property
    def provider_is_unwired(self) -> bool:
        return self._provider.source == UnwiredListProvider.source

    def screen_and_dispose(
        self,
        subject_id: str,
        subject_name: str,
        context: dict[str, Any] | None = None,
    ) -> DispositionCase:
        """Screen a subject and open a disposition case if matches clear threshold."""
        context = context or {}
        self._counter += 1
        case_id = f"sanc-{self._counter}"
        raw = self._provider.screen(subject_name, context)
        matches = tuple(m for m in raw if m.score >= self._threshold)

        case = DispositionCase(
            case_id=case_id,
            subject_id=subject_id,
            subject_name=subject_name,
            state=DispositionState.CLEARED if not matches else DispositionState.ON_HOLD,
            list_source=self._provider.source,
            matches=matches,
            provider_unwired=self.provider_is_unwired,
        )
        self._cases[case_id] = case
        self._log(case, AuditEventType.SANCTIONS_SCREENING, "screened")
        if matches:
            # The state machine actually transitions ON_HOLD -> ESCALATED; each
            # transition is recorded for the trail.
            self._append_history(case, "hold_opened")  # state is ON_HOLD here
            self._log(case, AuditEventType.SANCTIONS_HOLD, "hold_opened")
            case.state = DispositionState.ESCALATED
            self._append_history(case, "escalated_for_review")
            self._log(case, AuditEventType.SANCTIONS_ESCALATION, "escalated_for_review")
        return case

    def resolve_case(
        self,
        case_id: str,
        *,
        true_positive: bool,
        reviewer_id: str,
        credential: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> DispositionCase:
        """Human disposition of an escalated case.

        True-positive → ``BLOCKED`` and (if wired) the sovereign veto fires.
        False-positive → ``FALSE_POSITIVE_CLEARED``.

        When an ``authorizer`` is wired, a ``credential`` is **required**: it must
        resolve to an authenticated non-agent principal authorized for
        ``resolve_sanctions_case`` (the resolved principal becomes the recorded
        reviewer). Without an authorizer, disposition is advisory and recorded
        against the free-string ``reviewer_id``.
        """
        case = self._cases[case_id]
        if case.state not in (DispositionState.ESCALATED, DispositionState.ON_HOLD):
            raise ValueError(f"case {case_id} is in state {case.state.value}; nothing to resolve")
        reviewer_id = self._authorize_resolution(reviewer_id, credential, context or {})

        if true_positive:
            case.state = DispositionState.BLOCKED
            self._append_history(case, f"true_positive_by:{reviewer_id}")
            if self._veto is not None:
                self._veto.trigger(
                    VetoReason.SANCTIONS_HIT,
                    triggered_by=reviewer_id,
                    description=f"confirmed sanctions match on {case.subject_name!r} ({case_id})",
                )
            self._log(case, AuditEventType.SANCTIONS_DISPOSITION, "blocked")
        else:
            case.state = DispositionState.FALSE_POSITIVE_CLEARED
            self._append_history(case, f"false_positive_by:{reviewer_id}")
            self._log(case, AuditEventType.SANCTIONS_DISPOSITION, "false_positive_cleared")
        return case

    def _authorize_resolution(
        self, reviewer_id: str, credential: str | None, context: dict[str, Any]
    ) -> str:
        """Return the effective reviewer id, enforcing auth when an authorizer is wired."""
        if self._authorizer is None:
            return reviewer_id  # advisory: free-string reviewer, no auth gate
        if credential is None:
            raise SanctionsNotAuthorizedError(
                "a credential is required to resolve a case when an authorizer is wired"
            )
        principal = self._authorizer.authenticate(credential)
        if principal is None:
            raise SanctionsNotAuthorizedError("credential failed authentication")
        if principal.is_agent:
            raise SanctionsNotAuthorizedError("an agent principal may not resolve a sanctions case")
        if not self._authorizer.authorize(principal, self.RESOLVE_ACTION, context):
            raise SanctionsNotAuthorizedError(
                f"principal {principal.principal_id!r} not authorized to resolve sanctions cases"
            )
        return principal.principal_id

    def get(self, case_id: str) -> DispositionCase:
        return self._cases[case_id]

    def _append_history(self, case: DispositionCase, action: str) -> None:
        case.history.append({"action": action, "at": _now_iso(), "state": case.state.value})

    def _log(self, case: DispositionCase, event_type: AuditEventType, action: str) -> None:
        if self._chain is None:
            return
        self._chain.append(
            event_type,
            AutonomyLevel.A0_INFORMATIONAL,
            agent_id="banking-sanctions-workflow",
            payload={
                "case_id": case.case_id,
                "subject_id": case.subject_id,
                "action": action,
                "state": case.state.value,
                "list_source": case.list_source,
                "provider_unwired": case.provider_unwired,
                "match_count": len(case.matches),
            },
            actor_id="banking-sanctions-workflow",
        )
