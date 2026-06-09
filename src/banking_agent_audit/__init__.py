"""Governance patterns for autonomous AI agents in regulated banking.

Reference IP for adoption — not a control operating in production. The five
primitives are real, tested reference patterns; the banking controls
(model-risk effective challenge, ECOA/Reg B adverse-action gate) are
implemented and tested; the OFAC/sanctions surface ships as a reference
disposition *workflow* pattern against a pluggable list-provider interface
with NO bundled sanctions list (the list source is UNWIRED-BY-DEPLOYER).

Public API::

    from banking_agent_audit.governance import (
        AutonomyLadder,
        SovereignVeto,
        AuditChain,
        DEFCONMachine,
        EffectiveChallengeHarness,
        ModelRiskManagement,
        AdverseActionGate,
        SanctionsDispositionWorkflow,
    )

See README.md for the claim layer (implemented control vs documented pattern)
and docs/regulatory/ for the primary-sourced obligation mappings.
"""

from __future__ import annotations

__version__ = "0.1.2"

__all__ = ["__version__"]
