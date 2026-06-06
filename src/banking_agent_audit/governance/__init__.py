"""Banking governance primitives and controls.

Five corrected primitives (P1–P5) plus the 0.1.0 MUST-HAVE banking controls and
the OFAC/sanctions reference workflow. See each module's docstring for its
claim layer (implemented control vs documented pattern) and regulatory anchors.
"""

from __future__ import annotations

from banking_agent_audit.governance.adverse_action_gate import (
    AdverseActionDecision,
    AdverseActionGate,
    AdverseActionType,
    NoticeComplianceResult,
)
from banking_agent_audit.governance.audit_chain import (
    GENESIS_DOMAIN_SEPARATOR,
    GENESIS_HASH,
    AuditChain,
    AuditChainTamperError,
    InMemoryWitnessRegister,
    WitnessRegister,
    _compute_genesis_hash,
)
from banking_agent_audit.governance.autonomy_ladder import (
    LEVEL_REQUIRED_CONTROLS,
    AttestationVerifier,
    AutonomyLadder,
    ControlAttestation,
    PromotionDecision,
)
from banking_agent_audit.governance.defcon import (
    DEFCON,
    DEFCONMachine,
    DEFCONTransitionError,
    RiskMetrics,
)
from banking_agent_audit.governance.effective_challenge_harness import (
    ChallengeReport,
    EffectiveChallengeHarness,
    IndependenceAttestation,
    IndependenceDetector,
    Recommendation,
)
from banking_agent_audit.governance.model_risk_management import (
    ModelRecord,
    ModelRiskManagement,
    ModelRiskTier,
    ValidationStatus,
)
from banking_agent_audit.governance.sanctions_workflow import (
    DispositionCase,
    DispositionState,
    SanctionsDispositionWorkflow,
    SanctionsListProvider,
    SanctionsNotAuthorizedError,
    ScreeningMatch,
    UnwiredListProvider,
)
from banking_agent_audit.governance.sovereign_veto import (
    Authorizer,
    Principal,
    SovereignVeto,
    VetoNotAuthorizedError,
    VetoReason,
    VetoRecord,
)

__all__ = [
    # P1
    "AutonomyLadder",
    "AttestationVerifier",
    "ControlAttestation",
    "PromotionDecision",
    "LEVEL_REQUIRED_CONTROLS",
    # P2
    "SovereignVeto",
    "Authorizer",
    "Principal",
    "VetoReason",
    "VetoRecord",
    "VetoNotAuthorizedError",
    # P3
    "AuditChain",
    "AuditChainTamperError",
    "WitnessRegister",
    "InMemoryWitnessRegister",
    "GENESIS_HASH",
    "GENESIS_DOMAIN_SEPARATOR",
    "_compute_genesis_hash",
    # P4
    "DEFCON",
    "DEFCONMachine",
    "DEFCONTransitionError",
    "RiskMetrics",
    # P5
    "EffectiveChallengeHarness",
    "ChallengeReport",
    "IndependenceAttestation",
    "IndependenceDetector",
    "Recommendation",
    # banking controls
    "ModelRiskManagement",
    "ModelRecord",
    "ModelRiskTier",
    "ValidationStatus",
    "AdverseActionGate",
    "AdverseActionDecision",
    "AdverseActionType",
    "NoticeComplianceResult",
    # OFAC / sanctions reference workflow
    "SanctionsDispositionWorkflow",
    "SanctionsListProvider",
    "SanctionsNotAuthorizedError",
    "UnwiredListProvider",
    "ScreeningMatch",
    "DispositionCase",
    "DispositionState",
]
