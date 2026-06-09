"""Worked example — one ECOA / Regulation B adverse-action flow, end to end.

Companion to ``WORKED_EXAMPLE.md``. Runnable, stdlib + this library only:

    python examples/worked_example_adverse_action.py

It walks ONE concrete decision class — a model-driven credit denial that must
carry an ECOA / Reg B §1002.9 adverse-action notice (with the FCRA §615 overlay
when a consumer report drove the decision) — through five stations:

  1. The decision class and the autonomy rung the agent runs at.
  2. The agent drafts an adverse-action notice; the gate passes it.
  3. The hard envelope catches an out-of-envelope case (a thin-file / generic
     reason that does not state the specific, accurate basis required).
  4. The audit-chain entry that results — tamper-evident, replayable.
  5. The demotion trigger: reason-code drift over a window fires the sovereign
     veto and the DEFCON machine escalates, so the agent is demoted out of
     autonomous notice-drafting until a human clears it.

Every import path and call signature below is the real library API.
"""

from __future__ import annotations

from banking_agent_audit.governance import (
    DEFCON,
    AdverseActionDecision,
    AdverseActionGate,
    AdverseActionType,
    AuditChain,
    DEFCONMachine,
    RiskMetrics,
    SovereignVeto,
    VetoReason,
)
from banking_agent_audit.schemas.audit_event import AuditEventType


def _rule(title: str) -> None:
    print(f"\n{'=' * 68}\n{title}\n{'=' * 68}")


def draft_notice(applicant_id: str, reasons: tuple[str, ...], days: int) -> AdverseActionDecision:
    """Stand in for the agent: assemble the notice the model wants to send.

    A real agent fills these fields from the decision record; here we hand-build
    two notices — one well-formed, one out of envelope — to show the gate's job.
    """
    return AdverseActionDecision(
        applicant_id=applicant_id,
        action_type=AdverseActionType.DENIAL,
        principal_reasons=reasons,
        notice_provided=True,
        days_to_notice=days,
        used_consumer_report=True,
        cra_name_provided=True,
        credit_score_disclosed=True,
        applicant_rights_disclosed=True,
    )


def main() -> None:
    # --- Station 1: the decision class + the rung -------------------------
    _rule("1 · Decision class")
    print("Class : model-driven consumer-credit DENIAL")
    print("Notice: ECOA / Reg B §1002.9 adverse-action notice + FCRA §615 overlay")
    print("Rung  : the agent drafts notices autonomously (A3-style) under a veto")

    # One tamper-evident, deployer-keyed ledger underwrites the whole flow.
    chain = AuditChain(deployer_id="example-bank", mode="advisory")
    gate = AdverseActionGate(audit_chain=chain)

    # --- Station 2: the agent drafts a notice; the gate passes it ---------
    _rule("2 · Agent drafts a notice — in envelope")
    good = draft_notice(
        "app-1001",
        reasons=("debt-to-income ratio 0.62 exceeds the 0.43 product limit",),
        days=9,
    )
    good_result = gate.evaluate(good)
    print(f"applicant     : {good_result.applicant_id}")
    print(f"compliant     : {good_result.compliant}")
    print(f"violations    : {good_result.violations}")
    print(f"warnings      : {good_result.warnings}")
    print(f"citations      : {good_result.citations}")

    # --- Station 3: the hard envelope catches an out-of-envelope case ----
    _rule("3 · The hard envelope catches a thin-file / generic reason")
    # A thin-file applicant the model denied with a non-specific, checklist
    # reason — exactly the construction CFPB Circular 2022-03 forbids for a
    # complex model. The notice is "complete" on its face; the envelope is what
    # catches that the *reason* is not specific.
    bad = draft_notice(
        "app-1002",
        reasons=("score too low",),  # generic — no specific, accurate basis
        days=9,
    )
    bad_result = gate.evaluate(bad)
    print(f"applicant     : {bad_result.applicant_id}")
    print(f"compliant     : {bad_result.compliant}")
    print(f"warnings      : {bad_result.warnings}")
    drifted = bool(bad_result.warnings)
    print(f"reason-code drift flagged: {drifted}")

    # --- Station 4: the audit-chain entry that results -------------------
    _rule("4 · The audit-chain entry")
    print(f"events recorded     : {len(chain)}")
    print(f"ledger verifies      : {chain.verify()}")
    last = chain.events()[-1]
    print(f"last event type      : {last.event_type.value}")
    print(f"last event applicant : {last.payload['applicant_id']}")
    print(f"last event compliant : {last.payload['compliant']}")
    print(f"last event hash      : {last.event_hash[:16]}…  (chains to prev)")
    assert last.event_type is AuditEventType.ADVERSE_ACTION

    # --- Station 5: the demotion trigger fires on reason-code drift -------
    _rule("5 · Reason-code drift fires the demotion path")
    # The agent governs itself under a sovereign veto and a DEFCON machine, both
    # writing to the same ledger. A drift signal (a generic reason slipping
    # through) is a model-drift event: trip the veto and escalate DEFCON, which
    # demotes the agent out of autonomous notice-drafting until a human reviews.
    veto = SovereignVeto(agent_id="adverse-action-agent", audit_chain=chain)
    defcon = DEFCONMachine(audit_chain=chain)
    print(f"agent may draft (before)  : {veto.allow_execution()}")
    print(f"DEFCON (before)           : {defcon.current_level().name}")

    if drifted:
        veto.trigger(
            VetoReason.MODEL_DRIFT,
            triggered_by="monitor:reason-code-drift",
            description="generic adverse-action reason ('score too low') breached the envelope",
        )
        # Drift severe enough to demand a human: escalate the risk state machine.
        defcon.evaluate(RiskMetrics(consecutive_losses=8))

    print(f"agent may draft (after)   : {veto.allow_execution()}")
    print(f"DEFCON (after)            : {defcon.current_level().name}")
    print(f"veto reason               : {veto.active_record.reason.value}")
    assert veto.is_vetoed is True
    assert defcon.current_level() is DEFCON.HALT

    # A human (not the agent) clears the veto after review — the agent cannot
    # self-clear, and DEFCON only steps back down one guarded level at a time.
    veto.clear("reviewed; reason corrected to specific basis", operator_id="fair-lending-lead")
    defcon.manual_override(DEFCON.DANGER, "post-review step-down", operator_id="fair-lending-lead")
    print(f"agent may draft (cleared) : {veto.allow_execution()}")
    print(f"DEFCON (stepped down)     : {defcon.current_level().name}")

    _rule("Trail")
    print(f"total ledger events  : {len(chain)}")
    print(f"ledger still verifies : {chain.verify()}")
    print("Every station above wrote a hash-chained, replayable entry.")


if __name__ == "__main__":
    main()
