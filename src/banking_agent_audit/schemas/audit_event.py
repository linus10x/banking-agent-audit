"""The append-only audit-event schema and supporting enums.

An :class:`AuditEvent` is the unit hashed into the tamper-evident ledger
(:mod:`banking_agent_audit.governance.audit_chain`). The hash is computed over
a canonical JSON serialization of every field *except* ``event_hash`` itself,
so the stored hash can be independently recomputed and compared during
verification.

Within-trust-boundary tamper *evidence*, not tamper *prevention*: the chain
detects after-the-fact mutation; it does not stop a privileged in-process actor
from rewriting the store. See ``docs/FAILURE-MODES.md``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AutonomyLevel(Enum):
    """The Autonomy Ladder — A0 (read-only) through A4 (production autonomous).

    A proprietary governance framework. Each rung names the human-oversight
    posture an agent operates under; promotion is gated by the lower rungs'
    controls being attested (see :mod:`~.governance.autonomy_ladder`).
    """

    A0_INFORMATIONAL = "A0"  # Read-only; recommends, never writes.
    A1_ASSISTED = "A1"  # Drafts; a human approves every write.
    A2_DELEGATED = "A2"  # Writes inside an envelope; sampled human review.
    A3_SUPERVISED_AUTONOMOUS = "A3"  # Autonomous; sovereign veto + full audit.
    A4_PRODUCTION_AUTONOMOUS = "A4"  # A3 + orchestration + escalation.

    @property
    def rank(self) -> int:
        """Ordinal 0..4 for monotonic comparison."""
        return int(self.value[1:])

    @property
    def can_write(self) -> bool:
        """A0 is read-only; every rung above it may write."""
        return self is not AutonomyLevel.A0_INFORMATIONAL

    @property
    def requires_human_approval(self) -> bool:
        """A1 requires a human to approve every write before it lands."""
        return self in (
            AutonomyLevel.A0_INFORMATIONAL,
            AutonomyLevel.A1_ASSISTED,
        )


class AuditEventType(Enum):
    """The closed set of event types the governance primitives emit."""

    GENESIS = "genesis"
    AGENT_ACTION = "agent_action"
    LEVEL_GATE_EVALUATED = "level_gate_evaluated"
    VETO_TRIGGERED = "veto_triggered"
    VETO_CLEARED = "veto_cleared"
    DEFCON_TRANSITION = "defcon_transition"
    MODEL_VALIDATED = "model_validated"
    ADVERSE_ACTION = "adverse_action"
    SANCTIONS_SCREENING = "sanctions_screening"
    SANCTIONS_HOLD = "sanctions_hold"
    SANCTIONS_ESCALATION = "sanctions_escalation"
    SANCTIONS_DISPOSITION = "sanctions_disposition"
    WITNESS_ANCHOR = "witness_anchor"


class NonCanonicalPayloadError(TypeError):
    """Raised when a payload cannot be canonicalized without ambiguity.

    The ledger hash is the only integrity primitive, so a payload that would
    serialize ambiguously (non-string dict keys, non-JSON-native objects coerced
    via ``str``, non-finite floats) is rejected at construction rather than
    silently stringified into a forgeable preimage.
    """


def _canonicalize(obj: Any) -> Any:
    """Recursively normalize to an unambiguous, JSON-native structure.

    Rejects what would otherwise let two distinct payloads collide to the same
    hash: non-``str`` dict keys (JSON coerces all keys to strings), arbitrary
    objects (no silent ``str`` coercion), and non-finite floats. Tuples are
    normalized to lists so the in-memory and round-tripped forms agree.
    """
    if isinstance(obj, bool) or obj is None or isinstance(obj, (str, int)):
        return obj
    if isinstance(obj, float):
        if obj != obj or obj in (float("inf"), float("-inf")):  # NaN or +/-Inf
            raise NonCanonicalPayloadError(f"non-finite float in payload: {obj!r}")
        return obj
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            if not isinstance(key, str):
                raise NonCanonicalPayloadError(
                    f"payload dict keys must be str, got {type(key).__name__}: {key!r}"
                )
            out[key] = _canonicalize(value)
        return out
    if isinstance(obj, (list, tuple)):
        return [_canonicalize(x) for x in obj]
    raise NonCanonicalPayloadError(
        f"payload contains a non-JSON-native value of type {type(obj).__name__}: {obj!r}"
    )


def _canonical_json(obj: Any) -> str:
    """Deterministic JSON over an already-canonicalized structure.

    No ``default`` coercion and ``allow_nan=False`` — ambiguity is rejected
    upstream by :func:`_canonicalize`, so serialization here is total and exact.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class AuditEvent:
    """A single hash-chained ledger entry.

    ``event_hash`` is excluded from its own preimage; ``prev_hash`` links to the
    prior entry's ``event_hash`` (or the genesis seed for entry #0). The payload
    is canonicalized at construction; a non-canonicalizable payload raises
    :class:`NonCanonicalPayloadError`.
    """

    sequence: int
    event_type: AuditEventType
    autonomy_level: AutonomyLevel
    agent_id: str
    payload: dict[str, Any]
    timestamp: str
    prev_hash: str
    actor_id: str | None = None
    event_hash: str = field(default="")

    def __post_init__(self) -> None:
        # Normalize the payload to an unambiguous JSON-native form (frozen-safe).
        object.__setattr__(self, "payload", _canonicalize(self.payload))

    def _preimage(self) -> str:
        """The canonical string hashed to produce ``event_hash``."""
        return _canonical_json(
            {
                "sequence": self.sequence,
                "event_type": self.event_type.value,
                "autonomy_level": self.autonomy_level.value,
                "agent_id": self.agent_id,
                "payload": self.payload,
                "timestamp": self.timestamp,
                "prev_hash": self.prev_hash,
                "actor_id": self.actor_id,
            }
        )

    def compute_hash(self) -> str:
        """SHA-256 over the canonical preimage (excludes ``event_hash``)."""
        return hashlib.sha256(self._preimage().encode("utf-8")).hexdigest()

    def with_hash(self) -> AuditEvent:
        """Return a copy with ``event_hash`` populated from the preimage."""
        from dataclasses import replace

        return replace(self, event_hash=self.compute_hash())

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable view (e.g. for a JSONL ledger file)."""
        return {
            "sequence": self.sequence,
            "event_type": self.event_type.value,
            "autonomy_level": self.autonomy_level.value,
            "agent_id": self.agent_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
            "actor_id": self.actor_id,
            "event_hash": self.event_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditEvent:
        """Reconstruct an event from its :meth:`to_dict` form."""
        return cls(
            sequence=int(data["sequence"]),
            event_type=AuditEventType(data["event_type"]),
            autonomy_level=AutonomyLevel(data["autonomy_level"]),
            agent_id=str(data["agent_id"]),
            payload=dict(data["payload"]),
            timestamp=str(data["timestamp"]),
            prev_hash=str(data["prev_hash"]),
            actor_id=data.get("actor_id"),
            event_hash=str(data.get("event_hash", "")),
        )
