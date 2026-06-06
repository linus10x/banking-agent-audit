# ADR-0001 — Branch the genesis seed in the ledger verifier

**Status:** Accepted (0.1.0)

## Context

A hash-chain verifier that unconditionally seeds the genesis `prev_hash` from the
legacy `"0"*64` zero-seed raises a **false TAMPER** on a clean, deployer-keyed
chain: the first event's `prev_hash` is the deployer seed, but the verifier
expects the zero-seed, so the linkage check fails on an untampered chain.

## Decision

`AuditChain.genesis_seed()` **branches** on whether the chain is deployer-keyed:

- hardened (`deployer_id` set) → `_compute_genesis_hash(deployer_id, iso)`;
- legacy (`deployer_id is None`) → `GENESIS_HASH` (`"0"*64`).

Both `append` and `verify`/`verify_strict` use the *same* `genesis_seed()`, so a
clean hardened chain and a clean legacy chain both verify `True`, and the legacy
zero-seed is preserved (not globally removed).

## Consequences

- No false TAMPER on hardened chains; legacy chains remain backward-compatible.
- The seed is centralized, so the verifier cannot drift from the appender — this
  is asserted by AL-PROBE-03a and killed in the mutation pass.
- Deployer binding: two deployers' chains cannot be transplanted undetectably.
