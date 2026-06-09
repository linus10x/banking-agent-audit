# banking-agent-audit

**Governance patterns for autonomous AI agents in regulated banking.**

Reference IP for adoption — tamper-evident audit logging, a human-in-the-loop
kill switch, an autonomy-promotion gate, a risk-state machine, and an
effective-challenge harness, plus two implemented banking controls
(model-risk validation and an ECOA/Reg B adverse-action gate) and a sanctions
disposition-workflow pattern. Built to a corrected primitive standard, tested
against real public enforcement actions, and honest about what it implements
versus what it documents.

[![CI](https://github.com/linus10x/banking-agent-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/linus10x/banking-agent-audit/actions/workflows/ci.yml)
[![DOI](https://zenodo.org/badge/1260859533.svg)](https://doi.org/10.5281/zenodo.20564584)
![coverage](https://img.shields.io/badge/coverage-%E2%89%A590%25-brightgreen)
![python](https://img.shields.io/badge/python-3.12%2B-blue)
![license](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue)
![status](https://img.shields.io/badge/status-beta%20v0.1.1-orange)

**182 tests · ~99% coverage (≥90% gate) · 13/13 mutation kill · golden corpus of 8 real CFPB/DOJ/FinCEN matters · zero runtime deps · `mypy --strict` · 5 SHA-pinned CI workflows.**

---

## Why this exists for frontier autonomy stacks

The controls in this library are **domain-agnostic**. The DEFCON state machine, the non-overridable **sovereign veto** (a separate-process control the agent cannot switch off), the **hash-chain audit ledger** (it detects tampering within its trust boundary), the **hard envelopes with mechanical escalation**, the **sampled-review tripwires**, and **monitor-led promotion** were forged in real multi-agent production systems under consequence — and they apply directly to any high-stakes coordinated autonomy (vehicles, robots, agent swarms) where *invisible promotion* or *cascade failure* is unacceptable. The decision class is a parameter: this repo encodes it for **banking — model risk, ECOA/Reg B adverse action, BSA/AML/OFAC**, but the same A0→A4 deployment-authority structure lifts into any decision class without inheriting financial-services assumptions.

- **Framework + whitepaper:** [autonomy-ladder.io](https://autonomy-ladder.io)
- **Non-financial demo (under 60s):** [`finserv-agent-audit/examples/agent_coordination`](https://github.com/linus10x/finserv-agent-audit/tree/main/examples/agent_coordination) — the same veto / envelope / audit-chain / demotion primitives on a generic agent swarm.

> **For reviewers & safety teams:** every control here is falsifiable — the test suite (182 tests · 13/13 mutation kill · zero runtime deps) turns each rule into a runnable check, and the veto and ledger are infrastructure with operational properties (separate process boundary, distinct credentials, a gate the agent cannot reach; write-once retention). These are reference implementations for adoption, not deployed production controls.


## Part of the Autonomy Ladder™ family

Six co-equal regulated-vertical reference libraries implementing the **Autonomy Ladder** — a governance framework for autonomous AI in regulated operations (A0→A4, every rung demotable). **Framework + whitepaper: [autonomy-ladder.io](https://autonomy-ladder.io).**

| Vertical | Library |
|---|---|
| Cross-vertical financial services | [`finserv-agent-audit`](https://github.com/linus10x/finserv-agent-audit) |
| Banking (model risk · ECOA/Reg B · BSA/AML/OFAC) | **[`banking-agent-audit`](https://github.com/linus10x/banking-agent-audit)** |
| Payments (OFAC · Reg E · rail finality) | [`payments-agent-audit`](https://github.com/linus10x/payments-agent-audit) |
| Health-insurance payer (UM · prior auth · appeals) | [`payer-agent-audit`](https://github.com/linus10x/payer-agent-audit) |
| SEC-registered investment advisers (Advisers Act §206) | [`private-capital-agent-audit`](https://github.com/linus10x/private-capital-agent-audit) |
| Commercial real estate | [`cre-agent-audit`](https://github.com/linus10x/cre-agent-audit) |

---

## What this is — and what it is not

This library is **reference IP for adoption**, not a control operating inside a
bank today. Read the claim layer before you cite it:

| Surface | Claim |
|---|---|
| The five primitives (level-gate, sovereign veto, hash-chain ledger, DEFCON, effective challenge) | **Real, tested reference patterns** — within-trust-boundary tamper *evidence*, not a deployed G-SIB control wrapped in an org assurance apparatus. |
| Model-risk effective-challenge control | **Implemented and tested.** Gates a model's validation status on attested challenger independence. |
| ECOA / Reg B §1002.9 adverse-action gate | **Implemented and tested.** Validates notice structure, timing, specific-reason content, and the FCRA §615 overlay. |
| OFAC / sanctions screening | **A reference disposition *workflow* pattern only.** It ships **no sanctions list**; the list source is a pluggable seam labeled `UNWIRED-BY-DEPLOYER`. It is **not** an operating OFAC control. |
| HMDA, TILA/Reg Z, deposit/fraud, AVM QC | **Documented patterns** — described and mapped to primary sources, not enforced in code at 0.1.0. |

Every statutory citation below is cited to a primary source or marked `UNVERIFIED`.

---

## Disclaimer

This software and its documentation are provided for **reference and educational
purposes only**. They are **not legal, compliance, or regulatory advice**, do not
create an attorney–client relationship, and are not a substitute for a bank's
model-risk framework, its compliance program, or qualified counsel. Nothing here
**guarantees compliance** with the Bank Secrecy Act, ECOA / Regulation B, FCRA,
HMDA, TILA, Regulation E, OFAC sanctions programs, model-risk guidance, or any
other law or regulation. Statutory citations may be incomplete or become out of
date; **verify every citation against the primary source and qualified counsel**
before relying on it. Supervisory guidance referenced here is non-enforceable and
subject to revision — confirm it is current. The software is provided **"AS IS",
WITHOUT WARRANTY OF ANY KIND**, express or implied, and the author disclaims all
liability for any use. See [`LICENSE-MIT`](LICENSE-MIT) / [`LICENSE-APACHE`](LICENSE-APACHE).

---

## Quick start

```bash
pip install -e ".[dev,test-property]"
```

```python
from banking_agent_audit.governance import (
    AuditChain, SovereignVeto, AdverseActionGate, ModelRiskManagement,
)
from banking_agent_audit.governance.adverse_action_gate import (
    AdverseActionDecision, AdverseActionType,
)

# A tamper-evident, deployer-keyed audit ledger.
chain = AuditChain(deployer_id="example-bank", mode="advisory")

# An ECOA / Reg B §1002.9 adverse-action check.
gate = AdverseActionGate(audit_chain=chain)
result = gate.evaluate(AdverseActionDecision(
    applicant_id="app-001",
    action_type=AdverseActionType.DENIAL,
    principal_reasons=("debt-to-income ratio 0.62 exceeds the 0.43 product limit",),
    notice_provided=True,
    days_to_notice=12,
    used_consumer_report=True,
    cra_name_provided=True,
    credit_score_disclosed=True,
    applicant_rights_disclosed=True,
))
print(result.compliant, result.citations)
```

CLI:

```bash
banking-audit claims              # print the obligation claim sheet
banking-audit verify audit.jsonl  # verify a JSONL audit ledger
```

---

## The five primitives (corrected standard)

1. **Level-gate (A0→A4)** — refuses promotion when a lower rung's controls are
   unmet and requires **independent attestation** of its inputs, not
   caller-asserted booleans. Advisory by default and labeled as such; a strict
   `production` mode fails closed without a verifier.
2. **Sovereign veto** — a fail-closed kill switch. In `production` mode a wired
   authorizer is mandatory; clearing a veto requires an **authenticated**
   non-agent principal, and **an agent cannot clear its own veto**.
3. **Hash-chain ledger** — `verify()` / `verify_strict()` **branch the genesis
   seed** so a deployer-keyed (hardened) chain and a legacy chain both verify
   true. End-to-end regeneration is detectable via an external **witness anchor**
   that is non-optional in `production` mode.
4. **DEFCON state machine** — escalates immediately on a risk breach; **never
   auto-de-escalates**. Lowering the level requires the manual-override +
   authorizer path and may move only **one level at a time** (no one-call
   `HALT → NORMAL`).
5. **Effective challenge** — rejects `challenger == primary` in code and records
   an operator **independence attestation**; a model owner cannot self-challenge
   to a clean `accept_primary`.

These are built to the corrected standard directly — not copied from a sibling
library's source.

---

## Banking controls and sub-vertical coverage

| Obligation | Sub-vertical | Claim layer | Primary source |
|---|---|---|---|
| Model validation via effective challenge | Capital-markets / model risk | **Implemented** | OCC Bulletin 2026-13 (2026 revised MRM guidance; verified as of June 2026) |
| ECOA / Reg B §1002.9 adverse-action notice + FCRA §615 | Consumer credit | **Implemented** | 12 CFR §1002.9; 15 U.S.C. §1681m |
| Sanctions / AML disposition workflow (no bundled list) | AML / sanctions | **Deployer-wired pattern** | 31 U.S.C. §5318(h)/(g); 31 CFR Ch. X (BSA), Ch. V (OFAC) |
| HMDA / Reg C loan-level disclosure | Mortgage | Documented pattern | 12 CFR Part 1003 |
| TILA / Reg Z consumer-credit disclosure | Consumer credit | Documented pattern | 12 CFR Part 1026 |
| Reg E / EFTA error resolution + unauthorized-EFT liability | Deposit / payments / fraud | Documented pattern | 12 CFR Part 1005 |
| Interagency AVM quality-control standards | Mortgage | Documented pattern | Interagency AVM rule (2024) |

Regulators in scope: Federal Reserve · OCC · FDIC · CFPB (consumer credit) ·
FinCEN and OFAC (AML/sanctions). The model-risk concept of **effective
challenge** crystallized in SR 11-7 (rescinded 2026-04-17; verified as of
June 2026) and is carried
forward in principle under the 2026 revised interagency Model Risk Management
guidance; that guidance states generative and agentic AI models are not within
its scope, so deployers of such models demonstrate bounded operation through
their own frameworks. See [`docs/regulatory/`](docs/regulatory/) for the
per-obligation mappings.

### Wiring the seams by org size

The strong (`production`-mode) guarantees require a deployer to wire an
authorizer, an attestation verifier, and a witness. The
[`reference_adapters`](src/banking_agent_audit/reference_adapters.py) module
ships a minimum-viable-production path — a durable fsync'd file witness, an
HMAC-signed-token authorizer, and a single-external-attester verifier — so a
small bank or neobank is not stuck in advisory mode. An optional
`IndependenceDetector` seam adds a defense-in-depth cross-check on the
effective-challenge independence attestation. See [`docs/SIZING.md`](docs/SIZING.md)
for the per-size wiring table and retention floors.

---

## Testing and assurance

The platform is the proof. The suite is layered, and the hard cases come from
the real world:

- **Unit + contract** tests for every primitive, control, and obligation entry.
- **Property-based** tests (`hypothesis`) — thousands of generated cases across
  ledger verify/tamper/regenerate invariants, level-gate monotonicity, DEFCON
  transition algebra, and challenger≠primary.
- **Five AL-PROBES** in [`tests/adversarial/`](tests/adversarial/) — committed
  reproductions of the constructions that defeat a defective primitive, each
  asserting the corrected guarantee holds (one probe per primitive; AL-PROBE-02
  is the assurance home for veto un-self-clearability).
- **A golden corpus** of real, public, primary-sourced banking enforcement
  actions turned into fixtures that assert how the controls govern each
  category. The platform is the proof: the suite runs against named CFPB / DOJ /
  FinCEN matters of record — **Trustmark, City National, Trident Mortgage,
  Washington Trust, Citibank, Fifth Third, Townstone, and TD Bank** — spanning
  redlining, ECOA / Reg B adverse action, fair-lending model use, and BSA / AML /
  OFAC failures. See [`tests/golden/`](tests/golden/).
- **A mutation pass** ([`scripts/mutation_pass.py`](scripts/mutation_pass.py))
  that disables each security predicate and confirms a test kills it (100%).
- **Coverage gate** at 90% (currently ~99%), with `ruff`, `mypy --strict`,
  Bandit, CodeQL, OSV, and gitleaks in CI.

```bash
pytest -q --cov=src/banking_agent_audit --cov-fail-under=90
python scripts/mutation_pass.py
```

---

## Who this is for

- **Heads of Model Risk and second-line validation** standing up effective
  challenge for AI/agentic models where the validator's independence is the
  load-bearing question.
- **Fair-lending and compliance teams** who need an adverse-action notice that
  states specific, accurate reasons under ECOA/Reg B and the FCRA overlay.
- **AML / sanctions engineering** wiring a disposition workflow around a real
  list provider, with a tamper-evident trail of every screen, hold, and block.
- **Board, audit committee, CISO, CRO, and the engineer who runs it** — each
  reads a different layer; the claim layer is written so none of them is misled.

---

## Limitations

Read [`LIMITATIONS.md`](LIMITATIONS.md) and [`FAILURE-MODES.md`](FAILURE-MODES.md)
before relying on anything here. In short: this is reference IP, the sanctions
surface ships no list, the documented-pattern sub-verticals are not enforced in
code at 0.1.0, and reasoning-layer prompt-injection of the underlying model is
out of scope.

---

## Citation

Archived on Zenodo — concept DOI [`10.5281/zenodo.20564584`](https://doi.org/10.5281/zenodo.20564584)
(resolves to the latest version). See [`CITATION.cff`](CITATION.cff).

---

## License

Dual-licensed under [MIT](LICENSE-MIT) or [Apache-2.0](LICENSE-APACHE), at your
option.

---

## Author

Kunjar Bhaduri — North Texas Capital Investments.
