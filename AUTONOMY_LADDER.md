# The Autonomy Ladder in this library

`banking-agent-audit` is one of six regulated-vertical reference libraries that
implement the **Autonomy Ladder** — a governance framework for autonomous AI in
regulated operations. The framework defines five deployment-authority rungs,
A0→A4, **every rung demotable**: an agent earns its way up only when the lower
rungs' controls are attested, and any breach demotes it.

Framework + whitepaper: **[autonomy-ladder.io](https://autonomy-ladder.io)**.

## The rungs

| Rung | Posture | Required controls (this library) |
|---|---|---|
| **A0** Informational | Read-only; recommends, never writes | none |
| **A1** Assisted | Drafts; a human approves every write | human-approval workflow |
| **A2** Delegated | Writes inside an envelope; sampled human review | action envelope · sampled human review |
| **A3** Supervised autonomous | Autonomous; sovereign veto + full audit | sovereign veto · audit chain |
| **A4** Production autonomous | A3 + orchestration + escalation | orchestration guard · escalation path |

The rung-to-control mapping is encoded directly in
[`LEVEL_REQUIRED_CONTROLS`](src/banking_agent_audit/governance/autonomy_ladder.py).
Promotion is monotonic: the gate refuses a rung whose lower-rung controls are
unmet, refuses rung-skipping, and (in `production` mode) requires **independent
attestation** of each control rather than a caller-asserted boolean.

## How this library's primitives map to the rungs

| Primitive | What it guarantees | Rung it gates |
|---|---|---|
| **Level gate** (`AutonomyLadder`) | Refuses promotion on unmet/unattested lower-rung controls; advisory mode is labeled, production fails closed without a verifier | every rung — it *is* the A0→A4 control |
| **Sovereign veto** (`SovereignVeto`) | Fail-closed kill switch; an agent cannot clear its own veto; clearing is an authenticated human-oversight act | required at **A3+** |
| **Audit chain** (`AuditChain`) | Tamper-evident hash-chained ledger; deployer-keyed genesis; witness anchor detects regeneration in production | required at **A3+** |
| **DEFCON gate** (`DEFCONMachine`) | Escalates immediately on risk breach; never auto-de-escalates; de-escalation is one guarded level at a time | the demotion mechanism across all rungs |
| **Effective-challenge harness** (`EffectiveChallengeHarness`) | Rejects `challenger == primary`; records an independence attestation | qualifies a model before it operates at any writing rung |
| **Adverse-action gate** (`AdverseActionGate`) | Validates ECOA / Reg B §1002.9 notice structure, timing, specific reasons, and the FCRA §615 overlay | the banking decision-class control an A2+ agent operates under |
| **Sanctions workflow** (`SanctionsDispositionWorkflow`) | OFAC/BSA disposition pattern; ships **no list** (the source is a `UNWIRED-BY-DEPLOYER` seam) | the banking decision-class control an A2+ agent operates under |

## Demotion is the point

The rungs are not a one-way ratchet. The DEFCON machine escalates the moment a
risk metric breaches a threshold and **never** auto-lowers; the sovereign veto
halts the agent on any drift or breach; and lowering risk state requires an
authenticated, authorized human moving one guarded level at a time. The
[`WORKED_EXAMPLE.md`](WORKED_EXAMPLE.md) shows this concretely: reason-code drift
on an adverse-action notice trips the veto and escalates DEFCON to HALT, demoting
the agent out of autonomous drafting until a human reviews and steps it down.

See the framework at **[autonomy-ladder.io](https://autonomy-ladder.io)** and the
five other vertical libraries linked from the [README](README.md).
