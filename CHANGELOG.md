# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.4] — 2026-06-27

First distribution to PyPI via Trusted Publishing (packaging/release only, no code changes).

## [0.1.3] — 2026-06-09

Frontier-autonomy README section + 'for reviewers & safety teams' note; links the framework and the non-financial agent-coordination demo. No source changes.

## [0.1.2] — 2026-06-09

Documentation release: README upgraded to the conversion standard (Autonomy Ladder family block, one-line proof strip, named golden-corpus assurance). No source changes.

## [0.1.1] — 2026-06-06

Archival release for DOI minting. No source/behavior changes from 0.1.0.

### Added

- `.zenodo.json` providing native Zenodo metadata for DOI archival (the
  dual-licensed `CITATION.cff` is not relied on for the Zenodo record).

## [0.1.0] — 2026-06-05

Initial public-candidate release. Built to the corrected primitive standard;
**not** copied from a sibling library's source.

### Added

- **Five governance primitives** (corrected standard):
  - Autonomy-ladder level-gate (A0→A4) — refuses promotion on unmet lower-rung
    controls; requires independent attestation of its inputs; advisory by
    default, fail-closed `production` mode.
  - Sovereign veto — fail-closed kill switch; authenticated, un-self-clearable
    clearance; mandatory authorizer in `production` mode.
  - Hash-chain ledger — branched genesis seed (hardened and legacy chains both
    verify); witness-anchored regeneration detection, non-optional in
    `production` mode.
  - DEFCON state machine — immediate escalation, guarded one-step de-escalation,
    no one-call `HALT → NORMAL`.
  - Effective-challenge harness — rejects self-challenge in code; records an
    operator independence attestation; no self-validation to `accept_primary`.
- **Two implemented banking controls**:
  - Model Risk Management — validation status gated on attested challenger
    independence.
  - ECOA / Reg B §1002.9 adverse-action gate — notice structure, timing,
    specific-reason validation, and the FCRA §615 overlay.
- **Sanctions / AML disposition-workflow pattern** — screen → hold → escalate →
  veto against a pluggable list-provider seam (`UNWIRED-BY-DEPLOYER`); ships no
  bundled list.
- **Documented-pattern sub-verticals** — HMDA/Reg C, TILA/Reg Z, Reg E/EFTA,
  interagency AVM QC — mapped to primary sources in the obligation map.
- **Test & assurance suite** — property-based fuzzing (thousands of cases),
  five committed AL-PROBES, a golden corpus of real public enforcement actions,
  and a 100%-kill mutation pass over the security predicates; ~99% coverage.
- **CI** — `ruff`, `mypy --strict`, `pytest --cov-fail-under=90`, Bandit,
  CodeQL, OSV-Scanner, gitleaks; SHA-pinned actions.

### Hardened (post-adversarial-review)

- **Ledger integrity:** payloads are canonicalized at construction
  (`NonCanonicalPayloadError` on non-`str` keys, non-JSON objects, non-finite
  floats); genesis seed hashes each field independently; corrupt ledgers raise
  `AuditChainTamperError`; writes are `fsync`'d; `verify_regeneration_resistant()`
  fails closed on internal inconsistency. (ADR-0004)
- **Sovereign veto:** the governed agent can never clear its own veto regardless
  of the `is_agent` flag; identity comparison is casefold+strip-normalized.
- **DEFCON** rejects a raw-`int` target; **adverse-action gate** flags negative
  notice timing and blank reasons as violations; **effective challenge** unwraps
  `functools.partial`/`wraps` for the self-challenge check.
- **New seams:** an optional `IndependenceDetector` (defense-in-depth on the
  effective-challenge independence attestation) and a `reference_adapters` module
  (durable file witness, HMAC-signed-token authorizer, single-attester verifier)
  giving small deployers a minimum-viable-production path (`docs/SIZING.md`).
- **Regulatory accuracy:** BSA cite anchored to §5318(h)/(g); FCRA score
  disclosure attributed to §609(f) with the §615(h)/Reg V risk-based-pricing
  path noted; two golden-corpus matters re-routed from `adverse_action_gate` to
  `fair_lending_pattern` (they are redlining/pricing, not notice-deficiency
  cases); MRM obligation URL pointed at OCC Bulletin 2026-13.

### Claim layer

- The five primitives are reference patterns (within-trust-boundary tamper
  evidence), not a deployed bank control.
- The sanctions surface is a reference disposition workflow only and bundles no
  sanctions list.
- Documented-pattern sub-verticals are not enforced in code at 0.1.0.

[0.1.0]: https://github.com/linus10x/banking-agent-audit/releases/tag/v0.1.0
