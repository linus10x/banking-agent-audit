# Architecture

`banking-agent-audit` is a zero-runtime-dependency Python library. Everything is
built around one append-only structure (the hash-chain ledger) and a small set
of governance objects that write to it.

## Layers

```
  ┌─────────────────────────────────────────────────────────────┐
  │  Banking controls (implemented, tested)                     │
  │    ModelRiskManagement      AdverseActionGate               │
  ├─────────────────────────────────────────────────────────────┤
  │  Reference workflow pattern (deployer-wired)                │
  │    SanctionsDispositionWorkflow → pluggable list provider   │
  ├─────────────────────────────────────────────────────────────┤
  │  Five primitives (corrected standard)                       │
  │    AutonomyLadder  SovereignVeto  AuditChain                │
  │    DEFCONMachine   EffectiveChallengeHarness                │
  ├─────────────────────────────────────────────────────────────┤
  │  Schemas                                                    │
  │    AuditEvent · AutonomyLevel · AuditEventType              │
  └─────────────────────────────────────────────────────────────┘
                              │ writes to
                              ▼
                     AuditChain (hash-chained ledger)
```

## The trust boundary

The audit chain provides tamper **evidence**, not tamper **prevention**, within
a single trust boundary. A privileged in-process actor can rewrite the store;
what they cannot do is rewrite it *undetectably* — every mutation breaks the
hash linkage, and end-to-end regeneration breaks the external witness anchor.

The cross-boundary anchor is the `WitnessRegister` seam. The bundled
`InMemoryWitnessRegister` is a reference for tests and local demos; a real
deployment wires an external transparency log (e.g. a public-good timestamp
authority). In `production` mode the witness is non-optional — the chain refuses
to start without one.

## Mode discipline (advisory vs production)

Every stateful primitive takes a `mode`:

- **`advisory`** (default) — backward-compatible, does not fail closed, and is
  *labeled advisory* in every record it writes. An advisory clear of a veto, for
  example, is recorded as `authenticated=false, mode="advisory"`.
- **`production`** — a named strict opt-in. The dependency that makes the
  guarantee real (an authorizer for the veto and DEFCON de-escalation, a
  verifier for the level-gate, a witness for the ledger) becomes mandatory; its
  absence raises at construction.

This split is deliberate: the strong guarantee is opt-in so that adopting the
library never silently changes default behavior, and the advisory default never
*implies* enforcement it cannot deliver.

## Seams a deployer wires

| Seam | Protocol | What the deployer supplies |
|---|---|---|
| Authentication / authorization | `Authorizer` | An IdP/KMS that resolves a credential to a `Principal` and authorizes actions |
| Independent attestation | `AttestationVerifier` | Signature/identity verification confirming an attester is genuine and independent |
| External anchor | `WitnessRegister` | A transparency log recording chain heads outside the chain's storage |
| Sanctions list | `SanctionsListProvider` | A real watchlist/feed (`UNWIRED-BY-DEPLOYER` by default — no list bundled) |

## Data flow

A governance object (a veto trigger, a DEFCON transition, a model validation, an
adverse-action evaluation, a sanctions disposition) constructs a payload and
calls `AuditChain.append`, which seals the event into the chain. Verification
replays the chain from the branched genesis seed and recomputes every hash.
