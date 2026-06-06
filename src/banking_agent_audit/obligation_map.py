"""The executable claim sheet — banking obligations mapped to controls.

Each entry states, honestly, whether the obligation is met by an **implemented,
tested control** in this library, a **documented pattern** (described, not
enforced in code), or is **deployer-wired** (the library provides the seam, the
deployer supplies the substance). Every statutory cite is primary-sourced
against the canonical reg SSOT or marked ``UNVERIFIED``.

This map is asserted by tests so a buyer-facing claim cannot drift from what the
code actually does (the §1 Claim Sheet, made executable).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ClaimLayer(Enum):
    IMPLEMENTED_CONTROL = "implemented_control"
    DOCUMENTED_PATTERN = "documented_pattern"
    DEPLOYER_WIRED = "deployer_wired"


@dataclass(frozen=True)
class Obligation:
    obligation_id: str
    sub_vertical: str
    title: str
    citation: str
    source_url: str
    claim_layer: ClaimLayer
    module: str | None
    verified: bool  # False => carries an UNVERIFIED marker for owner/counsel


# Order: the two 0.1.0 MUST-HAVE controls first (implemented), then the
# documented-pattern sub-verticals, then the deployer-wired sanctions seam.
OBLIGATIONS: tuple[Obligation, ...] = (
    Obligation(
        obligation_id="mrm_effective_challenge",
        sub_vertical="capital_markets_model_risk",
        title="Model validation via effective challenge with independent challenger",
        citation="SR 11-7 (rescinded 2026-04-17) → 2026 revised interagency MRM guidance "
        "(OCC Bulletin 2026-13)",
        source_url="https://www.occ.gov/news-issuances/bulletins/2026/bulletin-2026-13.html",
        claim_layer=ClaimLayer.IMPLEMENTED_CONTROL,
        module="governance.model_risk_management",
        verified=True,
    ),
    Obligation(
        obligation_id="ecoa_reg_b_adverse_action",
        sub_vertical="consumer_credit",
        title="ECOA / Reg B §1002.9 adverse-action notice (specific reasons) + FCRA §615 overlay",
        citation="12 CFR §1002.9; 15 U.S.C. §1681m",
        source_url="https://www.consumerfinance.gov/rules-policy/regulations/1002/9/",
        claim_layer=ClaimLayer.IMPLEMENTED_CONTROL,
        module="governance.adverse_action_gate",
        verified=True,
    ),
    Obligation(
        obligation_id="bsa_aml_ofac_disposition",
        sub_vertical="aml_sanctions",
        title="Sanctions/AML screen→hold→escalate→veto disposition workflow (no bundled list)",
        citation="31 U.S.C. §5318(h) (AML program) + §5318(g) (SAR); umbrella §5311 et seq.; "
        "31 CFR Chapter X (BSA/AML); 31 CFR Chapter V (OFAC)",
        source_url="https://www.fincen.gov/resources/statutes-and-regulations",
        claim_layer=ClaimLayer.DEPLOYER_WIRED,
        module="governance.sanctions_workflow",
        verified=True,
    ),
    Obligation(
        obligation_id="hmda_reg_c",
        sub_vertical="mortgage",
        title="HMDA / Reg C loan-level data collection & fair-lending disclosure",
        citation="12 CFR Part 1003",
        source_url="https://www.consumerfinance.gov/rules-policy/regulations/1003/",
        claim_layer=ClaimLayer.DOCUMENTED_PATTERN,
        module=None,
        verified=True,
    ),
    Obligation(
        obligation_id="tila_reg_z",
        sub_vertical="consumer_credit",
        title="TILA / Reg Z consumer-credit disclosure",
        citation="15 U.S.C. §1601 et seq.; 12 CFR Part 1026",
        source_url="https://www.consumerfinance.gov/rules-policy/regulations/1026/",
        claim_layer=ClaimLayer.DOCUMENTED_PATTERN,
        module=None,
        verified=True,
    ),
    Obligation(
        obligation_id="reg_e_efta_fraud",
        sub_vertical="deposit_payments_fraud",
        title="Reg E / EFTA error-resolution & unauthorized-EFT liability "
        "(the compliance context for AI fraud decisioning, not a fraud-model mandate)",
        citation="12 CFR Part 1005",
        source_url="https://www.consumerfinance.gov/rules-policy/regulations/1005/",
        claim_layer=ClaimLayer.DOCUMENTED_PATTERN,
        module=None,
        verified=True,
    ),
    Obligation(
        obligation_id="avm_quality_control",
        sub_vertical="mortgage",
        title="Interagency AVM quality-control standards (incl. nondiscrimination)",
        citation="Interagency AVM rule, amending the agencies' respective parts (e.g. OCC 12 CFR "
        "Part 34; CFPB 12 CFR Part 1026 — confirm the operative part for the deployer's charter; "
        "Part 226 is the Board's legacy Reg Z)",
        source_url="https://www.federalregister.gov/documents/2024/08/07/2024-16197/"
        "quality-control-standards-for-automated-valuation-models",
        claim_layer=ClaimLayer.DOCUMENTED_PATTERN,
        module=None,
        verified=True,
    ),
)


def implemented() -> tuple[Obligation, ...]:
    """Obligations met by a tested, implemented control."""
    return tuple(o for o in OBLIGATIONS if o.claim_layer is ClaimLayer.IMPLEMENTED_CONTROL)


def documented_patterns() -> tuple[Obligation, ...]:
    return tuple(o for o in OBLIGATIONS if o.claim_layer is ClaimLayer.DOCUMENTED_PATTERN)


def deployer_wired() -> tuple[Obligation, ...]:
    return tuple(o for o in OBLIGATIONS if o.claim_layer is ClaimLayer.DEPLOYER_WIRED)
