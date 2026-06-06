"""P3 — Tamper-evident hash-chain ledger.

Built to the *corrected* primitive standard (do NOT replicate the upstream
defect where the verifier seeds the legacy ``"0"*64`` zero-seed unconditionally
and so raises a false TAMPER on a clean deployer-keyed chain):

* ``verify()`` / ``verify_strict()`` **branch the genesis prev-hash seed** on
  whether the chain is deployer-keyed. A hardened chain (``deployer_id`` set)
  seeds from :func:`_compute_genesis_hash`; a legacy chain (``deployer_id is
  None``) seeds from the ``"0"*64`` zero-seed. **Both verify ``True``.**
* End-to-end *regeneration* (rebuilding the whole chain with internally
  consistent hashes) is detectable via an external **witness anchor** that is
  **non-optional in production mode** — see :class:`WitnessRegister` and
  :meth:`AuditChain.verify_regeneration_resistant`.

PRODUCTION MODE is a named strict opt-in (``mode="production"``). In it a
missing witness register **fails closed** (the constructor refuses to start).
The default ``mode="advisory"`` constructor stays backward-compatible and is
labeled advisory in code and docs — it does NOT fail closed.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from banking_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

GENESIS_HASH = "0" * 64
GENESIS_DOMAIN_SEPARATOR = "banking-agent-audit/genesis/v1"


def _compute_genesis_hash(deployer_id: str, chain_creation_iso: str) -> str:
    """Deployer-keyed seed for the genesis prev-hash.

    Each field is hashed independently and the digests concatenated, so the
    delimiter cannot be smuggled across fields (``deployer="a", iso="b/c"`` and
    ``deployer="a/b", iso="c"`` produce **distinct** seeds). Binding the seed to
    a deployer identity means two deployers' chains cannot be transplanted
    without detection.
    """
    sep = hashlib.sha256(GENESIS_DOMAIN_SEPARATOR.encode("utf-8")).digest()
    dep = hashlib.sha256(deployer_id.encode("utf-8")).digest()
    iso = hashlib.sha256(chain_creation_iso.encode("utf-8")).digest()
    return hashlib.sha256(sep + dep + iso).hexdigest()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class AuditChainTamperError(Exception):
    """Raised by :meth:`AuditChain.verify_strict` on any inconsistency."""


@runtime_checkable
class WitnessRegister(Protocol):
    """External anchor seam (Rekor / OpenTimestamps / a regulator log).

    The reference :class:`InMemoryWitnessRegister` is for tests and local demos
    only; a production deployer wires a real transparency log here. The contract
    is: :meth:`anchor` records a chain head outside the chain's own storage, and
    :meth:`anchored_heads` returns every head ever anchored, so a regenerated
    chain (whose heads differ) is detectable.
    """

    def anchor(self, head_hash: str, timestamp: str) -> dict[str, Any]: ...

    def anchored_heads(self) -> list[str]: ...


class InMemoryWitnessRegister:
    """Reference, in-memory :class:`WitnessRegister`.

    NOT durable across processes — labeled a reference. A real deployment must
    substitute an external transparency log; this exists so the regeneration
    invariant is testable without network access.
    """

    def __init__(self) -> None:
        self._heads: list[str] = []

    def anchor(self, head_hash: str, timestamp: str) -> dict[str, Any]:
        self._heads.append(head_hash)
        return {"head_hash": head_hash, "timestamp": timestamp, "witness": "in-memory-reference"}

    def anchored_heads(self) -> list[str]:
        return list(self._heads)


class AuditChain:
    """Append-only, hash-chained, tamper-evident ledger.

    Parameters
    ----------
    log_file:
        Optional JSONL path; events are appended on write and loaded on init.
    deployer_id, chain_creation_iso:
        When ``deployer_id`` is supplied the chain is *hardened* — its genesis
        seed is deployer-keyed. When ``None`` the chain is *legacy* and seeds
        from the ``"0"*64`` zero-seed. Both verify ``True``.
    witness_register:
        External anchor seam. Required in ``production`` mode.
    mode:
        ``"advisory"`` (default, backward-compatible, does not fail closed) or
        ``"production"`` (strict opt-in: a missing witness register raises at
        construction).
    """

    GENESIS_HASH = GENESIS_HASH

    def __init__(
        self,
        *,
        log_file: Path | None = None,
        deployer_id: str | None = None,
        chain_creation_iso: str | None = None,
        witness_register: WitnessRegister | None = None,
        mode: str = "advisory",
    ) -> None:
        if mode not in ("advisory", "production"):
            raise ValueError(f"mode must be 'advisory' or 'production', got {mode!r}")
        if mode == "production" and witness_register is None:
            # Fail closed: P3 production mode requires a non-optional witness anchor.
            raise ValueError(
                "production mode requires a witness_register (fail-closed); "
                "the witness anchor is non-optional in production mode"
            )
        if mode == "production" and not deployer_id:
            # "production" implies a hardened (deployer-keyed) chain, not the
            # legacy '0'*64 seed.
            raise ValueError("production mode requires a non-empty deployer_id (a hardened chain)")
        self._mode = mode
        self._deployer_id = deployer_id
        self._chain_creation_iso = chain_creation_iso or _now_iso()
        self._witness = witness_register
        self._log_file = log_file
        self._store: list[AuditEvent] = []
        self._lock = threading.RLock()
        if log_file is not None and log_file.exists():
            self._load(log_file)

    # -- properties -------------------------------------------------------

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_hardened(self) -> bool:
        """True when the chain is deployer-keyed (not a legacy zero-seed chain)."""
        return self._deployer_id is not None

    def __len__(self) -> int:
        return len(self._store)

    def events(self) -> list[AuditEvent]:
        """A shallow copy of the event list (frozen events; safe to read)."""
        return list(self._store)

    # -- genesis seed branch (the corrected core) -------------------------

    def genesis_seed(self) -> str:
        """The prev-hash seed for entry #0 — branched on hardened vs legacy."""
        if self._deployer_id is not None:
            return _compute_genesis_hash(self._deployer_id, self._chain_creation_iso)
        return GENESIS_HASH

    def chain_head(self) -> str:
        """Current head hash; the genesis seed for an empty chain."""
        with self._lock:
            if not self._store:
                return self.genesis_seed()
            return self._store[-1].event_hash

    # -- append -----------------------------------------------------------

    def append(
        self,
        event_type: AuditEventType,
        autonomy_level: AutonomyLevel,
        agent_id: str,
        payload: dict[str, Any],
        actor_id: str | None = None,
    ) -> AuditEvent:
        """Append one event, chaining it to the current head."""
        with self._lock:
            event = AuditEvent(
                sequence=len(self._store),
                event_type=event_type,
                autonomy_level=autonomy_level,
                agent_id=agent_id,
                payload=payload,
                timestamp=_now_iso(),
                prev_hash=self.chain_head(),
                actor_id=actor_id,
            ).with_hash()
            self._store.append(event)
            if self._log_file is not None:
                self._persist(event)
            return event

    # -- verification (corrected: branched seed) --------------------------

    def verify(self) -> bool:
        """Soft variant — replay the chain, return ``False`` on any mismatch.

        Seeds from :meth:`genesis_seed`, so a clean hardened chain AND a clean
        legacy chain both return ``True`` (the corrected behavior).
        """
        with self._lock:
            prev = self.genesis_seed()
            for event in self._store:
                if event.event_hash != event.compute_hash():
                    return False
                if event.prev_hash != prev:
                    return False
                prev = event.event_hash
            return True

    def verify_strict(self) -> None:
        """Raise :class:`AuditChainTamperError` on the first inconsistency."""
        with self._lock:
            prev = self.genesis_seed()
            for index, event in enumerate(self._store):
                if event.event_hash != event.compute_hash():
                    raise AuditChainTamperError(
                        f"event_hash mismatch at index {index}: stored "
                        f"{event.event_hash[:12]}… != recomputed "
                        f"{event.compute_hash()[:12]}…"
                    )
                if event.prev_hash != prev:
                    raise AuditChainTamperError(
                        f"prev_hash mismatch at index {index}: links to "
                        f"{event.prev_hash[:12]}… expected {prev[:12]}…"
                    )
                prev = event.event_hash

    # -- witness anchoring (regeneration resistance) ----------------------

    def anchor_to_witness(self) -> dict[str, Any]:
        """Anchor the current head to the external witness; record the receipt.

        The receipt is also appended to the chain as a ``WITNESS_ANCHOR`` event
        so the receipt itself is hash-chained.
        """
        if self._witness is None:
            raise ValueError("no witness_register configured; cannot anchor")
        with self._lock:
            if not self._store:
                # Anchoring the genesis seed would never become an event_hash, so
                # regeneration resistance could not be proven against it.
                raise ValueError("cannot anchor an empty chain; append at least one event first")
            head = self.chain_head()
            receipt = self._witness.anchor(head, _now_iso())
            self.append(
                AuditEventType.WITNESS_ANCHOR,
                AutonomyLevel.A0_INFORMATIONAL,
                agent_id="banking-audit-chain",
                payload={"anchored_head": head, "receipt": receipt},
            )
            return receipt

    def verify_regeneration_resistant(self) -> bool:
        """Detect end-to-end regeneration via the external witness record.

        Fails closed on internal inconsistency first (so a forged event carrying
        a stale anchored hash with no valid linkage is caught), then requires
        every head the witness ever anchored to still appear as an ``event_hash``
        in the current, validly-linked chain. A regenerated chain drops those
        heads, so this returns ``False``.

        Scope: the witness only attests heads *up to each anchor*. Content
        appended after the last anchor is not yet witness-protected — anchor
        after each critical event (see ``docs/FAILURE-MODES.md``).
        """
        if self._witness is None:
            raise ValueError("no witness_register configured; cannot prove regeneration resistance")
        with self._lock:
            if not self.verify():  # fail closed: internal consistency is a precondition
                return False
            present = {e.event_hash for e in self._store}
            return all(head in present for head in self._witness.anchored_heads())

    # -- persistence ------------------------------------------------------

    def _persist(self, event: AuditEvent) -> None:
        assert self._log_file is not None
        with self._log_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def _load(self, log_file: Path) -> None:
        with log_file.open("r", encoding="utf-8") as fh:
            for index, raw in enumerate(fh):
                line = raw.strip()
                if not line:
                    continue
                try:
                    self._store.append(AuditEvent.from_dict(json.loads(line)))
                except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
                    # A truncated or corrupted ledger is a tamper/corruption
                    # signal, not an opaque crash that takes the audit subsystem
                    # down.
                    raise AuditChainTamperError(
                        f"corrupt ledger entry at line {index}: {exc}"
                    ) from exc
