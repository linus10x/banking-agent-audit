# Model Risk Management mapping — effective challenge

> **Not legal advice.** Reference mapping only; verify every citation against the
> primary source and counsel. See the README Disclaimer. Supervisory guidance is
> non-enforceable and subject to revision.

**Implemented control:** `governance/model_risk_management.py` +
`governance/effective_challenge_harness.py`.

## Primary sources

- **SR 11-7 — Guidance on Model Risk Management** (Federal Reserve / OCC 2011-12).
  Status: **rescinded 2026-04-17**. SR 11-7 is the origin of the load-bearing
  concept of *effective challenge* — critical analysis by objective, informed
  parties who can identify model limitations and assumptions and produce
  appropriate changes.
- **2026 revised interagency Model Risk Management guidance (OCC Bulletin
  2026-13)** — the joint Fed/OCC/FDIC guidance that supersedes SR 11-7 and
  SR 21-8 (issued April 17, 2026; non-enforceable supervisory guidance, most
  relevant to banking organizations with over $30B in total assets).
  Authoritative source (OCC Bulletin 2026-13):
  <https://www.occ.gov/news-issuances/bulletins/2026/bulletin-2026-13.html>.
  Per OCC Bulletin 2026-13, generative AI and agentic AI models "are not within
  the scope of this guidance"; institutions deploying such models demonstrate
  bounded operation through their own frameworks.

## How the control maps

| Requirement | Implementation |
|---|---|
| Effective challenge by an objective, independent party | `EffectiveChallengeHarness` rejects `challenger == primary` in code and records an operator `IndependenceAttestation`. |
| A model owner cannot validate their own model | Without attested independence the recommendation is forced to `ESCALATE`; `ModelRiskManagement.record_validation` cannot reach `APPROVED`. |
| Validation lifecycle / model inventory | `ModelRiskManagement` maintains a registered inventory with a per-model validation status and a tier (`ModelRiskTier`). |
| Documentation / replay | Each validation appends a `MODEL_VALIDATED` event with the eval-set hash and the full independence attestation to the audit chain. |

## Honesty notes

- Vendor-family and prompt-template independence are **attested, not
  code-detected** — the harness does not fabricate a detector; it records the
  operator's claim and who made it.
- This is a documented reference control, not a substitute for a bank's own
  model-risk framework, validation policy, or counsel.
