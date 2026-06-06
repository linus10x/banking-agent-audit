"""P5 — Effective-challenge harness (model-validation second line).

Built to the *corrected* primitive standard, in two parts:

* **(a) ENFORCE in code** — the challenger's identity must differ from the
  primary's. ``challenger_id == primary_id`` (or the same callable object) is
  rejected at construction, so ``disagreement_rate`` can never be forced to 0
  by self-challenge.
* **(b) RECORD as attestation** — an operator-supplied
  :class:`IndependenceAttestation` (not same owner / not same vendor family /
  not same prompt template) plus WHO chose the challenger and WHEN, written to
  the chain. Vendor-family and prompt-template independence are **attested, not
  code-detected** (no detector is fabricated). **A model owner cannot
  self-challenge to a clean ``ACCEPT_PRIMARY``**: when independence is not
  attested, the recommendation is forced to ``ESCALATE``.

Regulatory anchor: the "effective challenge" concept originating in SR 11-7
(rescinded 2026-04-17), carried forward in principle under the 2026 revised
interagency Model Risk Management guidance (OCC Bulletin 2026-13). Note OCC
Bulletin 2026-13 states generative and agentic AI models "are not within the
scope of this guidance" — so deployers of such models demonstrate bounded
operation through their own frameworks. See ``docs/regulatory/model_risk_mrm_mapping.md``.
"""

from __future__ import annotations

import functools
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from banking_agent_audit.governance.audit_chain import AuditChain
from banking_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class Recommendation(Enum):
    ACCEPT_PRIMARY = "accept_primary"
    INVESTIGATE = "investigate"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class IndependenceAttestation:
    """Operator's attestation of challenger independence (not code-detected).

    Independence holds only when none of the three "same" flags is set.
    """

    chosen_by: str
    same_owner: bool
    same_vendor_family: bool
    same_prompt_template: bool
    statement: str = ""
    chosen_at: str = field(default_factory=_now_iso)

    @property
    def is_independent(self) -> bool:
        return not (self.same_owner or self.same_vendor_family or self.same_prompt_template)


@runtime_checkable
class IndependenceDetector(Protocol):
    """Optional defense-in-depth seam that cross-checks the operator attestation.

    Independence is *attested* by an operator (not fabricated by this library).
    A deployer MAY additionally wire a detector that returns its own verdict:
    ``True`` (believes independent), ``False`` (believes NOT independent), or
    ``None`` (abstains). A ``False`` verdict overrides an "independent"
    attestation; the verdict and any disagreement are recorded to the chain.
    """

    def detect(
        self, primary_id: str, challenger_id: str, context: dict[str, Any]
    ) -> bool | None: ...


def _root_callable(fn: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Unwrap ``functools.partial`` and ``functools.wraps`` to the underlying fn.

    So a ``partial(primary)`` or a ``@wraps(primary)`` wrapper is still detected
    as the primary for the self-challenge check.
    """
    seen: set[int] = set()
    while True:
        if isinstance(fn, functools.partial):
            fn = fn.func
            continue
        wrapped = getattr(fn, "__wrapped__", None)
        if wrapped is not None and id(wrapped) not in seen:
            seen.add(id(wrapped))
            fn = wrapped
            continue
        return fn


@dataclass(frozen=True)
class ChallengeReport:
    primary_id: str
    challenger_id: str
    primary_accuracy: float
    challenger_accuracy: float
    disagreement_rate: float
    disagreement_examples: tuple[tuple[Any, Any, Any], ...]
    independent: bool
    recommendation: Recommendation
    eval_set_hash: str
    methodology: str = "effective_challenge_v1"


class EffectiveChallengeHarness:
    """Run a primary model against an independent challenger and record the result.

    Parameters
    ----------
    primary_model, challenger_model:
        Callables ``input -> output``.
    eval_set:
        ``[(input, expected_output), ...]``.
    independence:
        Operator's :class:`IndependenceAttestation` for the challenger.
    primary_id, challenger_id:
        Identities; ``challenger_id == primary_id`` is rejected.
    """

    def __init__(
        self,
        *,
        primary_model: Callable[[Any], Any],
        challenger_model: Callable[[Any], Any],
        eval_set: list[tuple[Any, Any]],
        independence: IndependenceAttestation,
        primary_id: str,
        challenger_id: str,
        audit_chain: AuditChain | None = None,
        independence_detector: IndependenceDetector | None = None,
        accept_threshold: float = 0.05,
        investigate_threshold: float = 0.30,
    ) -> None:
        if primary_id.strip().casefold() == challenger_id.strip().casefold():
            raise ValueError(
                "challenger_id must differ from primary_id "
                "(self-challenge is rejected — P5 enforce-in-code)"
            )
        if _root_callable(primary_model) is _root_callable(challenger_model):
            raise ValueError(
                "challenger_model must not be the same callable as primary_model "
                "(unwrapping partial/wraps)"
            )
        if not eval_set:
            raise ValueError("eval_set must be non-empty")
        if not 0.0 <= accept_threshold < investigate_threshold <= 1.0:
            raise ValueError("require 0 <= accept_threshold < investigate_threshold <= 1")
        self._primary = primary_model
        self._challenger = challenger_model
        self._eval_set = eval_set
        self._independence = independence
        self._primary_id = primary_id
        self._challenger_id = challenger_id
        self._chain = audit_chain
        self._detector = independence_detector
        self._accept = accept_threshold
        self._investigate = investigate_threshold

    def _eval_set_hash(self) -> str:
        # Provenance fingerprint of the eval set for the report only — NOT a
        # ledger-integrity gate. ``default=str`` is intentional here because eval
        # inputs/outputs are arbitrary model I/O, not necessarily JSON-native.
        blob = json.dumps(self._eval_set, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def run(self) -> ChallengeReport:
        """Evaluate both models; derive a recommendation; record to chain."""
        n = len(self._eval_set)
        primary_correct = 0
        challenger_correct = 0
        disagreements = 0
        examples: list[tuple[Any, Any, Any]] = []
        for inp, expected in self._eval_set:
            p = self._primary(inp)
            c = self._challenger(inp)
            if p == expected:
                primary_correct += 1
            if c == expected:
                challenger_correct += 1
            if p != c:
                disagreements += 1
                if len(examples) < 20:
                    examples.append((inp, p, c))

        disagreement_rate = disagreements / n
        detector_verdict = self._detector_verdict()
        independent = self._effectively_independent(detector_verdict)
        recommendation = self._recommend(disagreement_rate, independent)

        report = ChallengeReport(
            primary_id=self._primary_id,
            challenger_id=self._challenger_id,
            primary_accuracy=primary_correct / n,
            challenger_accuracy=challenger_correct / n,
            disagreement_rate=disagreement_rate,
            disagreement_examples=tuple(examples),
            independent=independent,
            recommendation=recommendation,
            eval_set_hash=self._eval_set_hash(),
        )
        self._record(report, detector_verdict)
        return report

    def _detector_verdict(self) -> bool | None:
        if self._detector is None:
            return None
        return self._detector.detect(self._primary_id, self._challenger_id, {})

    def _effectively_independent(self, detector_verdict: bool | None) -> bool:
        # A detector's NOT-independent verdict overrides an "independent"
        # attestation (defense-in-depth); it never upgrades a non-independent one.
        if detector_verdict is False:
            return False
        return self._independence.is_independent

    def _recommend(self, disagreement_rate: float, independent: bool) -> Recommendation:
        # A model owner cannot self-challenge to a clean accept: without
        # (effective) independence, escalate regardless of disagreement rate.
        if not independent:
            return Recommendation.ESCALATE
        if disagreement_rate <= self._accept:
            return Recommendation.ACCEPT_PRIMARY
        if disagreement_rate <= self._investigate:
            return Recommendation.INVESTIGATE
        return Recommendation.ESCALATE

    def _record(self, report: ChallengeReport, detector_verdict: bool | None) -> None:
        if self._chain is None:
            return
        self._chain.append(
            AuditEventType.MODEL_VALIDATED,
            AutonomyLevel.A0_INFORMATIONAL,
            agent_id=self._primary_id,
            payload={
                "challenger_id": self._challenger_id,
                "disagreement_rate": report.disagreement_rate,
                "recommendation": report.recommendation.value,
                "independent": report.independent,
                "detector_verdict": detector_verdict,
                "detector_attestation_disagree": (
                    detector_verdict is not None
                    and detector_verdict != self._independence.is_independent
                ),
                "independence_attestation": {
                    "chosen_by": self._independence.chosen_by,
                    "chosen_at": self._independence.chosen_at,
                    "same_owner": self._independence.same_owner,
                    "same_vendor_family": self._independence.same_vendor_family,
                    "same_prompt_template": self._independence.same_prompt_template,
                    "statement": self._independence.statement,
                },
                "eval_set_hash": report.eval_set_hash,
            },
            actor_id=self._independence.chosen_by,
        )
