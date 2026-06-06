# ADR-0004 — Canonicalize payloads; fail closed on ambiguity and corruption

**Status:** Accepted (0.1.0, post-adversarial-review hardening)

## Context

An adversarial review found that the ledger's only integrity primitive — the
SHA-256 over a JSON preimage — could be defeated:

- `json.dumps(..., default=str)` silently coerced arbitrary objects, so an
  object whose `str()` matched a target string collided with that string.
- JSON coerces all dict keys to strings, so `{1: "a"}` and `{"1": "a"}` hashed
  identically; tuples and lists also collided and drifted across a round-trip.
- `allow_nan=True` emitted non-standard `NaN`/`Infinity` tokens.
- A corrupt/truncated ledger file crashed construction with an opaque error.
- `verify_regeneration_resistant()` was a pure set-membership test, decoupled
  from `verify()`.

## Decision

- **Canonicalize at construction.** `AuditEvent.__post_init__` normalizes the
  payload via `_canonicalize`, which rejects non-`str` dict keys, non-JSON-native
  objects (no `str` coercion), and non-finite floats (`NonCanonicalPayloadError`),
  and normalizes tuples to lists. The preimage uses `allow_nan=False` and no
  `default`.
- **Genesis seed hashes each field independently** so the delimiter cannot be
  smuggled across fields.
- **Fail closed on corruption.** `_load` raises `AuditChainTamperError` with the
  line index; writes are flushed and `fsync`'d.
- **Regeneration resistance calls `verify()` first** (fails closed on internal
  inconsistency) before the witness-membership check.
- **Defense-in-depth on the veto:** the governed agent's `principal_id` can never
  clear its own veto, independent of the `is_agent` flag; identity comparison is
  casefold+strip-normalized.

## Consequences

- The integrity primitive is no longer forgeable via preimage ambiguity.
- Callers must pass JSON-native payloads (string keys, no custom objects) — a
  deliberate, documented constraint, enforced loudly rather than silently.
- Each guard is covered by a committed regression test and killed in the
  mutation pass.
