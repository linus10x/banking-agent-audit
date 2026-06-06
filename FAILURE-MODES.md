# Failure modes

How each primitive fails, what it does about it, and what it does *not* protect.

## Hash-chain ledger (`AuditChain`)

| Failure mode | Behavior |
|---|---|
| In-place event mutation (payload or `prev_hash`) | Detected: `verify()` returns `False`; `verify_strict()` raises `AuditChainTamperError` at the first inconsistent index. |
| End-to-end regeneration (rebuild the whole chain consistently) | `verify()` alone cannot catch this (the new chain is internally consistent). `verify_regeneration_resistant()` catches it: an anchored head absent from the chain proves regeneration. |
| Clean deployer-keyed chain | Verifies `True` — the genesis seed is branched, so a hardened chain is **not** a false TAMPER (the corrected behavior). |
| `production` mode with no witness or empty `deployer_id` | Fails closed at construction (production requires both a witness and a hardened, deployer-keyed chain). |
| In-memory witness lost on process exit | Regeneration resistance degrades to "demonstration only" — wire a durable external witness (`reference_adapters.FileWitnessRegister` for small scale, an external transparency log at G-SIB scale). Documented, not silent. |
| Persistence: JSONL file truncated/corrupted mid-line | `_load` raises `AuditChainTamperError` with the line index — a corrupt ledger is a tamper/corruption signal, not an opaque crash. Writes are flushed + `fsync`'d. |
| Ambiguous payload (non-`str` dict key, non-JSON object, non-finite float) | Rejected at `AuditEvent` construction (`NonCanonicalPayloadError`) — closes hash-collision/forgery vectors where two distinct payloads share a preimage. |
| Witness only attests heads up to each anchor | Content appended *after* the last anchor is not yet witness-protected. `verify_regeneration_resistant()` first fails closed on internal inconsistency, but the regeneration guarantee covers only the anchored prefix — **anchor after each critical event.** |

## Sovereign veto (`SovereignVeto`)

| Failure mode | Behavior |
|---|---|
| Agent attempts to clear its own veto | Rejected (`VetoNotAuthorizedError`). |
| Free-string `operator_id` used to clear in `production` | Rejected — a credential resolving to an authenticated principal is required. |
| Forged / unknown credential | Rejected at authentication. |
| Authenticated but unauthorized principal | Rejected at authorization. |
| In-memory veto state lost on restart | Documented: wire an `audit_chain` with a durable log file; the trigger/clear events are the recovery record. |

## DEFCON (`DEFCONMachine`)

| Failure mode | Behavior |
|---|---|
| One-call `HALT → NORMAL` | Rejected (`DEFCONTransitionError`); de-escalation is one level at a time. |
| Automatic de-escalation on calm metrics | Never happens — `evaluate()` only escalates or holds. |
| Unauthenticated de-escalation in `production` | Rejected; requires an authenticated non-agent principal. |
| Agent principal de-escalating | Rejected. |

## Level-gate (`AutonomyLadder`)

| Failure mode | Behavior |
|---|---|
| Promotion with a missing lower-rung control | Refused; falls back to the current level. |
| Rung-skip (jump more than one level) | Refused unless `allow_skip=True`. |
| Self-attested controls in `production` | Rejected — the verifier confirms the attester is independent of the requesting agent. |
| Advisory mode (no verifier) | Granted but labeled `verified=False` / "ADVISORY"; never implies enforcement. |

## Effective challenge (`EffectiveChallengeHarness`)

| Failure mode | Behavior |
|---|---|
| `challenger_id == primary_id` or same callable | Rejected at construction. |
| Owner self-challenge to a clean `accept_primary` | Impossible — without attested independence the recommendation is forced to `ESCALATE`. |
| Empty eval set / invalid thresholds | Rejected at construction. |

## Not defended

- Reasoning-layer prompt injection of the underlying model (see `LIMITATIONS.md`).
- Compromise of the deployer's IdP/KMS behind the `Authorizer` seam.
- Sanctions screening accuracy — the library bundles no list.
