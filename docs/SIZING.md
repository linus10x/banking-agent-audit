# Sizing guide — wiring the seams by organization size

The primitives' strong guarantees depend on three deployer-wired seams: an
`Authorizer`, an `AttestationVerifier`, and a `WitnessRegister`. A G-SIB wires
its own IdP/KMS and an external transparency log. A small bank or neobank needs
a credible path between **advisory** mode (which never implies enforcement) and
full G-SIB wiring. This guide gives that path, plus retention guidance, so the
control degrades gracefully rather than being all-or-nothing.

## The seams and a minimum-viable-production adapter for each

| Seam | Small / startup (MVP) | Mid-market | Large / G-SIB |
|---|---|---|---|
| `Authorizer` | `reference_adapters.SignedTokenAuthorizer` (HMAC bearer tokens against a deployer secret) | OIDC / SSO bridge | Enterprise IdP + KMS-backed approval |
| `AttestationVerifier` | `reference_adapters.SingleAttesterVerifier` (one named external attester; self-attestation rejected) | Internal validation function + signatures | Independent model-validation org + signed attestations |
| `WitnessRegister` | `reference_adapters.FileWitnessRegister` (durable, fsync'd append-only file) | File witness replicated off-host | External transparency log (OpenTimestamps / Rekor) |

The `reference_adapters` module ships all three. They are **production-acceptable
at small scale** — real HMAC authentication, a durable fsync'd witness, and a
self-attestation-rejecting verifier — not toys. They are not a substitute for an
external transparency log or a full IdP at G-SIB scale.

```python
from pathlib import Path
from banking_agent_audit.governance import AuditChain, SovereignVeto
from banking_agent_audit.reference_adapters import FileWitnessRegister, SignedTokenAuthorizer

witness = FileWitnessRegister(Path("/var/lib/bank/witness.jsonl"))
authz = SignedTokenAuthorizer(b"<deployer-secret>", allowed_actions={"compliance@bank": {"clear_veto"}})

chain = AuditChain(deployer_id="small-bank", witness_register=witness, mode="production")
veto = SovereignVeto(agent_id="credit-agent", authorizer=authz, mode="production", audit_chain=chain)
```

## Small-org attestation accommodation

The independence model assumes the "independent" challenger/attester is not the
requesting agent. In a small shop the validator and the model owner may be the
same person. Accommodations that preserve the guarantee:

- Name **one external attester** (a fractional model-risk advisor, an external
  auditor, a board member) as the `SingleAttesterVerifier`'s trusted attester.
  Self-attestation is still rejected, so the guarantee holds.
- For effective challenge, wire an optional `IndependenceDetector` so a heuristic
  can cross-check the attestation even when headcount is thin.
- If genuine independence cannot be established, the model stays `ESCALATED`,
  which is the honest outcome, not a failure of the library.

## Retention floors (deployer policy — not enforced by the library)

The library does not impose a retention period; these are recommended floors a
deployer encodes in its own policy, aligned to the longest applicable rule:

| Record | Recommended floor | Anchor |
|---|---|---|
| Audit-chain ledger | ≥ 6 years | SEC 17a-4-class electronic-records practice; align to the institution's records schedule |
| Adverse-action decisions | ≥ 25 months | ECOA / Reg B §1002.12(b) record-retention |
| BSA/AML disposition records | ≥ 5 years | BSA recordkeeping (31 CFR Chapter X) |
| Model-validation records | Model lifetime + retirement window | Interagency MRM guidance (OCC Bulletin 2026-13) |

These are starting points; confirm against the institution's charter, regulator,
and counsel. The library makes the records durable (with a file-backed witness
and an fsync'd ledger); the retention *period* is the deployer's policy.
