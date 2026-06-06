# BSA/AML + OFAC mapping — sanctions disposition workflow

> **Not legal advice.** Reference mapping only; verify every citation against the
> primary source and counsel. See the README Disclaimer.

**Deployer-wired reference pattern:** `governance/sanctions_workflow.py`.
**This is not an operating OFAC control and ships no sanctions list.**

## Primary sources

- **Bank Secrecy Act / Anti-Money Laundering** — the operative mandates are
  **31 U.S.C. §5318(h)** (AML compliance program) and **§5318(g)**
  (suspicious-activity reporting); umbrella **§5311 et seq.**; implementing
  rules at **31 CFR Chapter X**. FinCEN (Treasury).
  <https://www.fincen.gov/resources/statutes-and-regulations>. Customer
  identification, transaction monitoring, suspicious-activity reporting, and
  recordkeeping. "Financial institution" is defined at 31 CFR §1010.100(t).
  Note: this module implements a *disposition workflow*, not the
  transaction-monitoring / SAR-filing surface that §5318(g)/(h) also cover.
- **OFAC sanctions** — administered under IEEPA / TWEA and the OFAC regulations
  at 31 CFR Chapter V. Prohibits transactions with blocked persons and
  sanctioned jurisdictions.

## How the pattern maps

| Element | Implementation |
|---|---|
| Screening against a watchlist | A pluggable `SanctionsListProvider` seam. The default `UnwiredListProvider` (source `UNWIRED-BY-DEPLOYER`) bundles **no list** and returns no matches. |
| Hold on a potential match | A match at/above threshold opens a case in `ON_HOLD` → `ESCALATED`. |
| Escalation to a reviewer | Recorded as a `SANCTIONS_ESCALATION` event. |
| Human disposition | `resolve_case(true_positive=...)` — a true positive moves to `BLOCKED` and (if wired) fires the sovereign veto; a false positive clears. |
| Audit trail | Every screen, hold, escalation, and disposition is appended to the chain, including `provider_unwired`. |

## Honesty notes

- The value of this module is the **disposition workflow and its trail**, not
  sanctions data. It claims only a *reference disposition pattern*.
- A deployment that does not wire a real provider cannot silently appear to pass:
  each case records `provider_unwired=true`.
- Screening accuracy, list freshness, fuzzy-matching quality, and false-positive
  rates are entirely the deployer's wired provider — out of scope here.
