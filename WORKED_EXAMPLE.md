# Worked example — one ECOA / Reg B adverse-action flow

This is the shortest path from "what does this library do" to "I watched it
catch a real failure." It walks **one** decision class — a model-driven consumer
credit denial that must carry an ECOA / Regulation B §1002.9 adverse-action
notice — end to end, using the real library API.

Run it yourself (stdlib + this library only, zero runtime deps):

```bash
pip install -e .
python examples/worked_example_adverse_action.py
```

The source is [`examples/worked_example_adverse_action.py`](examples/worked_example_adverse_action.py).
Every import path and call signature in this document is the real API.

---

## The decision class

A bank's credit agent denies an application. ECOA / Reg B §1002.9 requires an
adverse-action notice that states the **specific** principal reasons; when a
consumer report drove the decision, the FCRA §615 overlay (15 U.S.C. §1681m)
adds the CRA disclosure, the credit-score disclosure, and the applicant-rights
disclosure. CFPB Circular 2022-03 is explicit that a generic or checklist reason
that does not reflect the actual basis — common when a complex model is in the
loop — does not satisfy §1002.9(b)(2).

So the load-bearing question is not "did we send a notice." It is "does the
notice state a reason specific and accurate enough to be lawful." That is the
gap a model-driven pipeline silently widens, and it is exactly what the
`AdverseActionGate` is built to catch.

---

## Station 1 — the rung and the ledger

The agent drafts notices autonomously under a sovereign veto (an A3-style
posture). One tamper-evident, deployer-keyed ledger underwrites the whole flow.

```python
from banking_agent_audit.governance import AdverseActionGate, AuditChain

chain = AuditChain(deployer_id="example-bank", mode="advisory")
gate = AdverseActionGate(audit_chain=chain)
```

## Station 2 — the agent drafts a notice; the gate passes it

A well-formed denial: a specific debt-to-income reason, inside the timing window,
with the FCRA overlay populated.

```python
from banking_agent_audit.governance import AdverseActionDecision, AdverseActionType

good = AdverseActionDecision(
    applicant_id="app-1001",
    action_type=AdverseActionType.DENIAL,
    principal_reasons=("debt-to-income ratio 0.62 exceeds the 0.43 product limit",),
    notice_provided=True,
    days_to_notice=9,
    used_consumer_report=True,
    cra_name_provided=True,
    credit_score_disclosed=True,
    applicant_rights_disclosed=True,
)
result = gate.evaluate(good)
# result.compliant is True; result.violations is ()
# result.citations -> ('12 CFR §1002.9', '15 U.S.C. §1681m (FCRA §615)')
```

## Station 3 — the hard envelope catches an out-of-envelope case

A thin-file applicant the model denied with a non-specific, checklist reason.
The notice is complete on its face — every field is set — but the **reason**
is generic. The envelope catches what a field-presence check would miss.

```python
bad = AdverseActionDecision(
    applicant_id="app-1002",
    action_type=AdverseActionType.DENIAL,
    principal_reasons=("score too low",),  # generic — no specific, accurate basis
    notice_provided=True,
    days_to_notice=9,
    used_consumer_report=True,
    cra_name_provided=True,
    credit_score_disclosed=True,
    applicant_rights_disclosed=True,
)
flagged = gate.evaluate(bad)
# flagged.warnings carries the §1002.9(b)(2) + Circular 2022-03 specificity warning
```

The gate is deliberately honest about what it can and cannot certify: a generic
reason is a **warning** routed to human review (the gate cannot know the actual
decision basis), while a *blank* reason or a missing FCRA disclosure is a hard
**violation**. It flags the likely-insufficient reason; it does not pretend to
certify sufficiency.

## Station 4 — the audit-chain entry that results

Each evaluation writes a hash-chained, replayable entry. Nothing is taken on
trust; the ledger replays and verifies.

```python
print(len(chain))            # 2 — one entry per evaluation
print(chain.verify())        # True — the chain replays clean
last = chain.events()[-1]
print(last.event_type.value) # 'adverse_action'
print(last.payload["applicant_id"], last.payload["compliant"])
```

## Station 5 — the demotion trigger fires on reason-code drift

A generic reason slipping through is a model-drift signal. The agent governs
itself under a `SovereignVeto` and a `DEFCONMachine`, both writing to the same
ledger. Drift trips the veto and escalates the risk state machine — which
**demotes** the agent out of autonomous notice-drafting until a human reviews.

```python
from banking_agent_audit.governance import (
    DEFCON, DEFCONMachine, RiskMetrics, SovereignVeto, VetoReason,
)

veto = SovereignVeto(agent_id="adverse-action-agent", audit_chain=chain)
defcon = DEFCONMachine(audit_chain=chain)

veto.trigger(
    VetoReason.MODEL_DRIFT,
    triggered_by="monitor:reason-code-drift",
    description="generic adverse-action reason ('score too low') breached the envelope",
)
defcon.evaluate(RiskMetrics(consecutive_losses=8))   # escalates to HALT

assert veto.allow_execution() is False               # agent is demoted/halted
assert defcon.current_level() is DEFCON.HALT
```

A human — never the agent — clears the veto after review, and DEFCON steps back
down one guarded level at a time. The agent cannot self-clear, and there is no
one-call `HALT → NORMAL`.

```python
veto.clear("reviewed; reason corrected to specific basis", operator_id="fair-lending-lead")
defcon.manual_override(DEFCON.DANGER, "post-review step-down", operator_id="fair-lending-lead")
```

---

## What this demonstrates

| Property | Where it shows up |
|---|---|
| The decision class is encoded, not described | `AdverseActionGate.evaluate` returns structured violations/warnings/citations |
| The hard envelope catches the judgment call | a complete-on-its-face notice with a generic reason is flagged, not passed |
| Failure is evidence, not a crash | every evaluation appends a hash-chained `ADVERSE_ACTION` entry |
| Drift demotes autonomy | the veto halts the agent and DEFCON escalates; only a human steps it back |
| The whole trail is replayable | `chain.verify()` is `True` before and after |

For the framework these primitives implement — the A0→A4 rungs and the rest of
the family — see [`AUTONOMY_LADDER.md`](AUTONOMY_LADDER.md) and
[autonomy-ladder.io](https://autonomy-ladder.io).
