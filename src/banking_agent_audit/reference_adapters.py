"""Reference seam adapters — a minimum-viable-production path for small buyers.

The primitives' strong guarantees require a deployer to wire the seams (an
authorizer, an attestation verifier, a witness). A G-SIB wires its own IdP/KMS
and an external transparency log. A small bank or neobank needs a credible path
between "advisory" and full G-SIB wiring — these adapters are that path.

They are **production-acceptable at small scale**, not toys:

* :class:`FileWitnessRegister` — a durable, fsync'd, append-only witness file.
  Survives process restart (unlike ``InMemoryWitnessRegister``). For stronger
  guarantees a deployer still graduates to an external transparency log.
* :class:`SignedTokenAuthorizer` — an HMAC-signed bearer-token authorizer. Real
  cryptographic authentication against a deployer secret; a small shop can issue
  tokens without standing up a full IdP.
* :class:`SingleAttesterVerifier` — trusts a configured set of external
  attesters and rejects self-attestation. A small org names one external
  attester rather than running an attestation service.

See ``docs/SIZING.md`` for retention floors and the wiring guide by org size.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from pathlib import Path
from typing import Any

from banking_agent_audit.governance.autonomy_ladder import ControlAttestation
from banking_agent_audit.governance.sovereign_veto import Principal


class FileWitnessRegister:
    """A durable, append-only, fsync'd witness file (a real ``WitnessRegister``).

    Each anchored head is appended as a JSON line and flushed to disk, so the
    record survives a process restart. Concurrency-safe via a lock.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        if not path.exists():
            path.touch()

    def anchor(self, head_hash: str, timestamp: str) -> dict[str, Any]:
        receipt = {"head_hash": head_hash, "timestamp": timestamp, "witness": "file-reference"}
        with self._lock, self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(receipt, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return receipt

    def anchored_heads(self) -> list[str]:
        with self._lock:
            heads: list[str] = []
            for line in self._path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    heads.append(str(json.loads(line)["head_hash"]))
            return heads


class SignedTokenAuthorizer:
    """An HMAC-signed bearer-token ``Authorizer``.

    A token is ``"<principal_id>:<is_agent>:<hex-hmac>"``. The HMAC is over
    ``"<principal_id>:<is_agent>"`` keyed by the deployer secret, so a token
    cannot be forged without the secret. ``allowed_actions`` (per principal_id)
    governs authorization; ``None`` allows all actions for a principal.
    """

    def __init__(
        self,
        secret: bytes,
        *,
        allowed_actions: dict[str, set[str]] | None = None,
    ) -> None:
        if not secret:
            raise ValueError("secret must be non-empty")
        self._secret = secret
        self._allowed = allowed_actions or {}

    def issue(self, principal_id: str, *, is_agent: bool = False) -> str:
        """Mint a signed token for a principal (a real deployer would do this in its IdP)."""
        body = f"{principal_id}:{int(is_agent)}"
        return f"{body}:{self._sign(body)}"

    def _sign(self, body: str) -> str:
        return hmac.new(self._secret, body.encode("utf-8"), hashlib.sha256).hexdigest()

    def authenticate(self, credential: str) -> Principal | None:
        parts = credential.rsplit(":", 1)
        if len(parts) != 2:
            return None
        body, sig = parts
        if not hmac.compare_digest(sig, self._sign(body)):
            return None
        principal_id, _, is_agent_flag = body.partition(":")
        if not principal_id or is_agent_flag not in ("0", "1"):
            return None
        return Principal(principal_id=principal_id, is_agent=is_agent_flag == "1")

    def authorize(self, principal: Principal, action: str, context: dict[str, Any]) -> bool:
        allowed = self._allowed.get(principal.principal_id)
        return allowed is None or action in allowed


class SingleAttesterVerifier:
    """An ``AttestationVerifier`` that trusts a named set of external attesters.

    Verifies ``True`` only when the attestation's ``attester_id`` is in the
    trusted set AND is not the requesting agent — a small-org accommodation that
    still forbids self-attestation. (Signature verification is the deployer's to
    add; this checks identity and independence.)
    """

    def __init__(self, trusted_attesters: set[str]) -> None:
        if not trusted_attesters:
            raise ValueError("at least one trusted attester is required")
        self._trusted = trusted_attesters

    def verify(self, attestation: ControlAttestation, requesting_agent_id: str) -> bool:
        # Normalize so a case/whitespace variant of the agent's own id cannot
        # slip past the self-attestation block.
        if attestation.attester_id.strip().casefold() == requesting_agent_id.strip().casefold():
            return False
        return attestation.attester_id in self._trusted
