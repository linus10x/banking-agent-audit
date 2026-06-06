# ECOA / Regulation B §1002.9 mapping — adverse-action notices

> **Not legal advice.** Reference mapping only; verify every citation against the
> primary source and counsel. See the README Disclaimer.

**Implemented control:** `governance/adverse_action_gate.py`.

## Primary sources

- **ECOA / Regulation B §1002.9 — Notifications** (12 CFR §1002.9). CFPB.
  <https://www.consumerfinance.gov/rules-policy/regulations/1002/9/>.
  Requires notification of action taken, timing, and — on adverse action — a
  statement of the **specific principal reasons** (§1002.9(b)(2)). Applies to
  all creditors.
- **FCRA §615 — Adverse Action Notices** (15 U.S.C. §1681m). FTC / CFPB.
  <https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act>.
  When consumer-report information drives an adverse action, the user must
  provide the notice, the **credit score + key factors** (§615(a)(2), which
  incorporates the §609(f) / 15 U.S.C. §1681g(f) score disclosure — the key-factor
  content derives from §609(f), not from §615 itself), the **consumer reporting
  agency's name/address/phone** (§615(a)(3)), and the **consumer's rights** to a
  free report and to dispute (§615(a)(4)). Note the **separate risk-based pricing
  notice** path at §615(h) / Reg V (12 CFR Part 1022 subpart H), which is the
  other way a score reaches the consumer and is a common exam finding.
- **CFPB Circular 2022-03** — creditors using complex algorithms must still
  provide accurate, specific reasons; generic or checklist reasons that do not
  reflect the actual basis are insufficient.

## How the control maps

| Requirement | Implementation |
|---|---|
| Notice must be given | `notice_provided` checked; absence is a violation. |
| Timing (§1002.9(a)(1)) | `days_to_notice` vs a configurable `notice_deadline_days` (default 30; confirm exceptions against the regulation). |
| Specific principal reasons (§1002.9(b)(2)) | Empty reasons are a violation; likely-generic reasons raise a warning for human review (CFPB Circular 2022-03). |
| FCRA §615 overlay | When `used_consumer_report`, the CRA identity, score disclosure, and applicant-rights disclosures are each required. |
| Audit trail | Each evaluation appends an `ADVERSE_ACTION` event. |

## Honesty notes (reg-citation discipline)

- The control **does not author a Regulation B reason-code enumeration from
  memory.** Regulation B requires the *specific* reasons; the illustrative
  sample reasons live in **Appendix C to Part 1002**. The generic-reason markers
  in code are a heuristic aid for human review, **not** an authoritative list and
  **not** a certification of sufficiency.
- The notice-timing default is a configurable parameter, not a legal
  determination for any specific creditor's facts. `UNVERIFIED` for precise
  exceptions — confirm against §1002.9(a)(1) or route to counsel.
