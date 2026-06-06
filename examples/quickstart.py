"""End-to-end quickstart: a production-mode governance stack for a credit agent.

Run: python examples/quickstart.py
"""

from __future__ import annotations

from typing import Any

from banking_agent_audit.governance import (
    AdverseActionGate,
    AuditChain,
    InMemoryWitnessRegister,
    ModelRiskManagement,
    ModelRiskTier,
    SovereignVeto,
    VetoReason,
)
from banking_agent_audit.governance.adverse_action_gate import (
    AdverseActionDecision,
    AdverseActionType,
)
from banking_agent_audit.governance.effective_challenge_harness import (
    EffectiveChallengeHarness,
    IndependenceAttestation,
)
from banking_agent_audit.governance.sovereign_veto import Principal


class DemoAuthorizer:
    """A stand-in IdP — a real deployer wires their own."""

    def authenticate(self, credential: str) -> Principal | None:
        return Principal("chief-credit-officer", is_agent=False) if credential == "cco" else None

    def authorize(self, principal: Principal, action: str, context: dict[str, Any]) -> bool:
        return True


def main() -> None:
    authorizer = DemoAuthorizer()
    chain = AuditChain(
        deployer_id="example-bank",
        witness_register=InMemoryWitnessRegister(),
        mode="production",
    )

    # 1) Validate the underwriting model with an INDEPENDENT challenger.
    mrm = ModelRiskManagement(audit_chain=chain)
    mrm.register(
        "pd-model-v3", owner="quant", purpose="underwriting", risk_tier=ModelRiskTier.TIER_1_HIGH
    )
    report = EffectiveChallengeHarness(
        primary_model=lambda x: x >= 0.5,
        challenger_model=lambda x: x >= 0.55,
        eval_set=[(0.9, True), (0.1, False), (0.6, True)],
        independence=IndependenceAttestation(
            chosen_by="head-of-model-risk",
            same_owner=False,
            same_vendor_family=False,
            same_prompt_template=False,
        ),
        primary_id="pd-model-v3",
        challenger_id="challenger-vendor-b",
        audit_chain=chain,
    ).run()
    print("model validation:", mrm.record_validation("pd-model-v3", report).value)

    # 2) A fail-closed sovereign veto the agent cannot self-clear.
    veto = SovereignVeto(
        agent_id="credit-agent", authorizer=authorizer, mode="production", audit_chain=chain
    )
    veto.trigger(VetoReason.RISK_LIMIT_BREACH, "monitor", "exposure limit breached")
    print("vetoed:", veto.is_vetoed)
    veto.clear("limit restored after review", credential="cco")
    print("cleared by authenticated officer:", not veto.is_vetoed)

    # 3) An ECOA/Reg B adverse-action notice check.
    gate = AdverseActionGate(audit_chain=chain)
    res = gate.evaluate(
        AdverseActionDecision(
            applicant_id="app-77",
            action_type=AdverseActionType.DENIAL,
            principal_reasons=("debt-to-income ratio 0.61 exceeds the 0.43 product limit",),
            notice_provided=True,
            days_to_notice=9,
            used_consumer_report=True,
            cra_name_provided=True,
            credit_score_disclosed=True,
            applicant_rights_disclosed=True,
        )
    )
    print("adverse-action compliant:", res.compliant)

    # 4) The whole trail is tamper-evident and witness-anchored.
    chain.anchor_to_witness()
    print("ledger verifies:", chain.verify())
    print("regeneration-resistant:", chain.verify_regeneration_resistant())
    print("events recorded:", len(chain))


if __name__ == "__main__":
    main()
