# Assurance guide

How the library's primitives and controls map to the assurance frameworks a
bank's three lines of defense and its examiners actually use. Every row is
labeled **implemented control**, **documented pattern**, or **deployer-wired** —
no row implies a tested control that is not built.

## Framework alignment

| Framework | Where it touches | Claim |
|---|---|---|
| **Model Risk Management** — 2026 revised interagency MRM guidance (OCC Bulletin 2026-13, superseding SR 11-7) | `EffectiveChallengeHarness`, `ModelRiskManagement` | Implemented: effective challenge with attested challenger independence; validation status gated on it. Supervisory guidance, not an enforcement substitute. |
| **SOX 404 ITGC** (change/access/audit-trail integrity) | `AuditChain` | Implemented: tamper-evident, append-only, independently verifiable event log within the trust boundary. |
| **SOC 2 CC7.x** (detection & monitoring) | `DEFCONMachine`, `SovereignVeto` | Implemented: risk-state escalation and a fail-closed kill switch with an authenticated, recorded clearance path. |
| **FFIEC IT examination** (audit, BSA/AML) | `AuditChain`, `SanctionsDispositionWorkflow` | Mixed: audit trail implemented; sanctions disposition is a deployer-wired pattern with no bundled list. |
| **ECOA / Reg B + FCRA** (fair lending, adverse action) | `AdverseActionGate` | Implemented: notice structure, timing, specific-reason validation, FCRA §615 overlay. |
| **Resilience / TPRM** (durability, vendor seams) | `reference_adapters`, `production` mode | Mixed: a durable fsync'd file witness + HMAC authorizer + single-attester verifier ship as a minimum-viable-production path (`docs/SIZING.md`); retention floors are deployer policy, not enforced. |
| **BCBS 239** (risk-data aggregation & lineage) | `AuditChain` | Documented pattern: the chain provides event lineage; full aggregation is the deployer's. |
| **EU AI Act Art. 14** (human oversight) | `SovereignVeto`, `AutonomyLadder` | Implemented: human-in-the-loop veto; autonomy-promotion gate. |

## Three lines of defense

- **First line (business / model owners):** register models, run the
  effective-challenge harness, consult the veto and DEFCON gates before acting.
  The owner *cannot* self-validate a model to `APPROVED` or self-clear a veto.
- **Second line (model risk, compliance):** independence is the load-bearing
  control. Validation status is gated on an attested independent challenger;
  adverse-action notices are checked for specific, accurate reasons.
- **Third line (internal audit) and examiners:** the hash-chain ledger is the
  evidence. `verify_strict()` replays it; `verify_regeneration_resistant()`
  checks the external witness. Every veto, transition, validation, and
  disposition is in the trail with its actor and authentication status.

## What an examiner should test first

1. **Ledger integrity** — mutate a stored event; confirm `verify()` fails.
   Regenerate the chain; confirm the witness catches it.
2. **Veto un-self-clearability** — present an agent credential; confirm refusal.
3. **Model independence gate** — record a same-owner challenge; confirm it
   cannot reach `APPROVED`.
4. **Adverse-action completeness** — a denial driven by a consumer report with
   no FCRA disclosures must be flagged non-compliant.
5. **DEFCON guard** — attempt a one-call `HALT → NORMAL`; confirm refusal.

These are exactly the five AL-PROBES plus the control tests — committed,
runnable, and reproducible (`pytest tests/adversarial/`,
`scripts/mutation_pass.py`).
