# Limitations

Read this before relying on anything in this library. The discipline here is to
match the claim to the implemented reality.

## Scope of the claim

- **Reference IP, not a production control.** The primitives are tested
  reference patterns. They are not a deployed bank control wrapped in an
  organizational assurance apparatus, and nothing here has governed real money
  or real customers.
- **Tamper evidence, not tamper prevention.** The hash-chain ledger detects
  after-the-fact mutation within a single trust boundary. A privileged
  in-process actor can still rewrite the store; the guarantee is that they
  cannot do so undetectably once a witness anchor is in place.
- **In-memory reference witness.** `InMemoryWitnessRegister` is not durable
  across processes. Regeneration resistance is only as strong as the *external*
  witness a deployer wires; with the in-memory reference it is a demonstration,
  not a control.

## Sanctions / AML

- **No bundled sanctions list.** `SanctionsDispositionWorkflow` ships no OFAC
  SDN list or any other watchlist. The list source is `UNWIRED-BY-DEPLOYER`. The
  library provides the screen → hold → escalate → veto disposition workflow and
  its audit trail — not sanctions data, and not an operating OFAC control.
- A deployment that forgets to wire a real provider does not silently "pass":
  every disposition records `provider_unwired=true`.

## Documented-pattern sub-verticals

- **HMDA / Reg C, TILA / Reg Z, Reg E / EFTA, the interagency AVM rule** ship as
  *documented patterns* at 0.1.0 — mapped to primary sources, not enforced in
  code. The obligation map labels them `documented_pattern`; do not read them as
  implemented controls.

## Regulatory content

- **Reason codes are not authored from memory.** The adverse-action gate does
  not assert an authoritative Regulation B reason-code enumeration. It validates
  that deployer-supplied reasons are *specific* and flags likely-generic ones;
  the authoritative reasons live in the Regulation B appendix and the creditor's
  actual decision basis.
- **The notice-timing window is configurable, not a legal determination.** The
  30-day default is a parameter; confirm §1002.9(a)(1) and its exceptions
  against the regulation for the creditor's facts.
- **Model-risk supervisory guidance.** Effective challenge originates in SR 11-7
  (rescinded 2026-04-17) and is carried forward in principle under the 2026
  revised interagency Model Risk Management guidance (OCC Bulletin 2026-13),
  which states generative and agentic AI models are not within its scope. This
  library is a documented reference control, not a substitute for a bank's own
  model-risk framework or counsel.

## Out of scope

- **Reasoning-layer prompt injection.** Manipulating the underlying model's
  reasoning through crafted inputs is out of scope; this library governs the
  *actions* an agent may take and records them, it does not defend the model's
  cognition.
- **Cryptographic key management.** The `Authorizer` / `AttestationVerifier`
  seams are where a deployer's IdP/KMS lives; the library does not manage keys.

## No public matter cleanly tests adverse-action *notice sufficiency*

Mirroring the model-risk honesty above: the public fair-lending enforcement
record is dominated by **redlining/discouragement** (e.g. discouraging
prospective applicants) and **disparate-impact pricing** matters, not by
adverse-action-*notice*-content deficiencies. So the golden corpus routes those
matters to `fair_lending_pattern`, and the `adverse_action_gate` control is
validated by its own unit/property tests and a representative scenario rather
than by a public notice-deficiency consent order. The gate validates notice
*structure*; it does not certify that a creditor's stated reasons are the actual
basis of the decision.

## Sizing and graceful degradation

`production` mode fails closed without a wired authorizer, verifier, and witness
— which a small organization may not have on day one. `docs/SIZING.md` documents
a minimum-viable-production path (the `reference_adapters`) and a small-org
attestation accommodation so the control degrades gracefully across sizes. The
library does not impose a retention window; recommended floors are in
`docs/SIZING.md` and remain the deployer's policy.

## Honesty about the golden corpus

The golden corpus contains real, public matters of record with primary-source
URLs. There is **no clean public SR 11-7 model-risk enforcement action** — bank
model-risk deficiencies are handled through confidential supervisory channels —
so the algorithmic-model anchor is a *no-violation* fair-lending investigation
finding, labeled as such. Some fair-lending and sanctions matters involve
nonbank entities; those are labeled `is_depository_bank=false`.
