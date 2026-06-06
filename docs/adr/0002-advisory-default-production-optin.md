# ADR-0002 — Advisory default, fail-closed production opt-in

**Status:** Accepted (0.1.0)

## Context

A governance primitive that defaults to enforcing (mandatory authorizer, witness,
or verifier) is a breaking change for any caller and risks *implying* a guarantee
the deployment has not wired. A primitive that only ever advises can be mistaken
for an enforcing control.

## Decision

Every stateful primitive takes `mode`:

- **`advisory`** (default) — backward-compatible, does not fail closed, and is
  **labeled advisory** in every record it writes (e.g. a veto cleared in advisory
  mode records `authenticated=false, mode="advisory"`).
- **`production`** — a named strict opt-in in which the dependency that makes the
  guarantee real becomes mandatory and its absence **raises at construction**:
  the `Authorizer` (sovereign veto, DEFCON de-escalation), the
  `AttestationVerifier` (level-gate), and the `WitnessRegister` (ledger).

## Consequences

- Adopting the library never silently changes default behavior.
- The advisory default never implies enforcement it cannot deliver — honesty is
  encoded in the recorded events, not just the docs.
- Flipping the default to enforcing in a future version would be a MAJOR bump.
