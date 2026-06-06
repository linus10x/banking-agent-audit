"""Golden corpus — REAL, public, matter-of-record banking enforcement actions.

Every entry is a publicly announced matter of record sourced to an official
.gov page (CFPB, DOJ, FinCEN, OFAC/Treasury, NYDFS). Each carries a
``primary_source_url`` and a ``verified`` flag; nothing here invents allegations
or outcomes. These drive the parametrized fixtures in ``test_golden_corpus.py``,
which assert how this library's controls / obligation map would have *governed*
the category the matter falls into.

Sourced 2026-06-05 via live web search of primary regulator pages.

Honest caveat (model risk): there is **no clean public SR 11-7 model-risk
enforcement action** — bank model-risk deficiencies are handled through
confidential supervisory channels (MRAs/MRIAs), not public orders. The NYDFS
Apple Card report (a *no-violation* finding) is the closest verifiable public
algorithmic-model matter and is labeled as such; the SR 11-7 anchor itself is
supervisory guidance, not an enforcement action.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoldenCase:
    case_id: str
    name: str
    agency: str
    year: int
    citation: str
    primary_source_url: str
    matter_of_record: str
    penalty_amount_usd: int | None
    which_control: str  # adverse_action_gate | model_risk_management | sanctions_workflow | fair_lending_pattern
    verified: bool
    is_depository_bank: bool
    note: str = ""


CORPUS: tuple[GoldenCase, ...] = (
    # --- Category A: fair-lending / redlining consent orders ---
    GoldenCase(
        case_id="trustmark_redlining_2021",
        name="United States / CFPB / OCC v. Trustmark National Bank",
        agency="DOJ + CFPB + OCC",
        year=2021,
        citation="Fair Housing Act; ECOA (15 U.S.C. §1691)",
        primary_source_url="https://www.consumerfinance.gov/about-us/newsroom/cfpb-doj-and-occ-take-action-against-trustmark-national-bank-for-deliberate-discrimination-against-black-and-hispanic-families/",
        matter_of_record=(
            "DOJ, CFPB, and OCC alleged Trustmark engaged in a pattern or practice of redlining "
            "majority-Black and Hispanic neighborhoods in the Memphis area (2014–2018) in "
            "violation of the Fair Housing Act and ECOA; resolved for a $5M penalty plus a "
            "$3.85M loan-subsidy fund."
        ),
        penalty_amount_usd=5_000_000,
        which_control="fair_lending_pattern",
        verified=True,
        is_depository_bank=True,
    ),
    GoldenCase(
        case_id="city_national_redlining_2023",
        name="United States v. City National Bank",
        agency="DOJ",
        year=2023,
        citation="Fair Housing Act; ECOA",
        primary_source_url="https://www.justice.gov/archives/opa/pr/justice-department-secures-over-31-million-city-national-bank-address-lending-discrimination",
        matter_of_record=(
            "DOJ alleged City National redlined majority-Black and Hispanic neighborhoods of Los "
            "Angeles County (2017–2020) in violation of the Fair Housing Act and ECOA; settled for "
            "over $31M — the largest redlining settlement in DOJ history at the time."
        ),
        penalty_amount_usd=31_000_000,
        which_control="fair_lending_pattern",
        verified=True,
        is_depository_bank=True,
    ),
    GoldenCase(
        case_id="trident_redlining_2022",
        name="United States / CFPB v. Trident Mortgage Company",
        agency="DOJ + CFPB",
        year=2022,
        citation="Fair Housing Act; ECOA",
        primary_source_url="https://www.consumerfinance.gov/about-us/newsroom/cfpb-doj-order-trident-mortgage-company-to-pay-more-than-22-million-for-deliberate-discrimination-against-minority-families/",
        matter_of_record=(
            "DOJ and CFPB alleged Trident redlined majority-minority neighborhoods in the "
            "Philadelphia metro (2015–2019); resolved for more than $22M — DOJ's first redlining "
            "settlement with a non-bank lender."
        ),
        penalty_amount_usd=22_000_000,
        which_control="fair_lending_pattern",
        verified=True,
        is_depository_bank=False,
        note="Nonbank mortgage lender; relevant to the mortgage sub-vertical.",
    ),
    GoldenCase(
        case_id="washington_trust_redlining_2023",
        name="United States v. The Washington Trust Company",
        agency="DOJ",
        year=2023,
        citation="Fair Housing Act; ECOA",
        primary_source_url="https://www.justice.gov/archives/opa/pr/justice-department-secures-9-million-agreement-washington-trust-company-resolve-redlining",
        matter_of_record=(
            "DOJ alleged Washington Trust redlined majority-Black and Hispanic neighborhoods in "
            "Rhode Island (2016–2021) in violation of the Fair Housing Act and ECOA; settled for $9M."
        ),
        penalty_amount_usd=9_000_000,
        which_control="fair_lending_pattern",
        verified=True,
        is_depository_bank=True,
    ),
    # --- Category B: ECOA / Reg B discrimination & adverse-action ---
    GoldenCase(
        case_id="citibank_armenian_ecoa_2023",
        name="In re Citibank, N.A. (CFPB)",
        agency="CFPB",
        year=2023,
        citation="ECOA / Regulation B (12 CFR Part 1002); CFPB File No. 2023-CFPB-0013",
        primary_source_url="https://www.consumerfinance.gov/enforcement/actions/citibank-n-a/",
        matter_of_record=(
            "CFPB found Citibank intentionally discriminated against credit-card applicants it "
            "believed to be of Armenian national origin (2015–2021) by applying extra scrutiny and "
            "denials, in violation of ECOA/Reg B; ordered $1.4M redress + $24.5M penalty."
        ),
        penalty_amount_usd=25_900_000,
        which_control="adverse_action_gate",
        verified=True,
        is_depository_bank=True,
    ),
    GoldenCase(
        case_id="fifth_third_auto_ecoa_2015",
        name="United States / CFPB v. Fifth Third Bank",
        agency="DOJ + CFPB",
        year=2015,
        citation="ECOA (15 U.S.C. §1691)",
        primary_source_url="https://www.consumerfinance.gov/about-us/newsroom/cfpb-takes-action-against-fifth-third-bank-for-auto-lending-discrimination-and-illegal-credit-card-practices/",
        matter_of_record=(
            "DOJ and CFPB alleged Fifth Third charged African-American and Hispanic indirect-auto "
            "borrowers higher discretionary dealer markups than similarly situated non-Hispanic "
            "white borrowers in violation of ECOA; $18M settlement."
        ),
        penalty_amount_usd=18_000_000,
        which_control="fair_lending_pattern",
        verified=True,
        is_depository_bank=True,
        note="Disparate-impact dealer-markup pricing matter — a fair-lending case, "
        "not an adverse-action-notice (§1002.9) case.",
    ),
    GoldenCase(
        case_id="townstone_ecoa_discouragement_2024",
        name="CFPB v. Townstone Financial, Inc.",
        agency="CFPB",
        year=2024,
        citation="ECOA / Regulation B; N.D. Ill.",
        primary_source_url="https://www.consumerfinance.gov/enforcement/actions/townstone-financial-inc-and-barry-sturner/",
        matter_of_record=(
            "CFPB alleged Townstone discouraged prospective African-American applicants in the "
            "Chicago area from applying for mortgages in violation of ECOA's prohibition on "
            "discouraging prospective applicants; settled Nov 2024 for a $105,000 penalty."
        ),
        penalty_amount_usd=105_000,
        which_control="fair_lending_pattern",
        verified=True,
        is_depository_bank=False,
        note="ECOA §1002.4(b) discouragement / redlining matter (7th Cir. 2024), not an "
        "adverse-action-notice case; nonbank mortgage broker.",
    ),
    # --- Category C: BSA/AML and OFAC sanctions ---
    GoldenCase(
        case_id="td_bank_bsa_aml_2024",
        name="United States v. TD Bank, N.A.",
        agency="DOJ + FinCEN + OCC + Federal Reserve",
        year=2024,
        citation="Bank Secrecy Act (31 U.S.C. §5318); 18 U.S.C. §1956",
        primary_source_url="https://www.justice.gov/archives/opa/pr/td-bank-pleads-guilty-bank-secrecy-act-and-money-laundering-conspiracy-violations-18b",
        matter_of_record=(
            "TD Bank pleaded guilty to conspiring to fail to maintain a BSA-compliant AML program "
            "and to launder money (failures left a large share of transaction volume unmonitored); "
            "~$3.09B total resolution across agencies — the largest BSA penalty on record."
        ),
        penalty_amount_usd=3_090_000_000,
        which_control="sanctions_workflow",
        verified=True,
        is_depository_bank=True,
        note="penalty_amount_usd = aggregate multi-agency resolution; DOJ portion ~$1.8B.",
    ),
    GoldenCase(
        case_id="usaa_fsb_bsa_2022",
        name="In re USAA Federal Savings Bank (FinCEN / OCC)",
        agency="FinCEN + OCC",
        year=2022,
        citation="Bank Secrecy Act (31 U.S.C. §5318(h))",
        primary_source_url="https://www.fincen.gov/news/news-releases/fincen-announces-140-million-civil-money-penalty-against-usaa-federal-savings",
        matter_of_record=(
            "USAA FSB admitted it willfully failed to maintain a BSA-compliant AML program "
            "(2016–2021) and failed to timely/accurately report suspicious transactions; "
            "$140M total ($80M FinCEN + $60M OCC)."
        ),
        penalty_amount_usd=140_000_000,
        which_control="sanctions_workflow",
        verified=True,
        is_depository_bank=True,
    ),
    GoldenCase(
        case_id="wells_fargo_ofac_2023",
        name="OFAC Settlement with Wells Fargo Bank, N.A.",
        agency="OFAC (Treasury) + Federal Reserve",
        year=2023,
        citation="IEEPA-based sanctions (Iran/Syria/Sudan programs)",
        primary_source_url="https://ofac.treasury.gov/recent-actions/20230330",
        matter_of_record=(
            "OFAC found Wells Fargo (via legacy trade-finance software, 2008–2015) committed 124 "
            "apparent violations of the Iran, Syria, and Sudan sanctions programs; Wells Fargo "
            "remitted $30M to OFAC (with a separate ~$67.8M Federal Reserve penalty)."
        ),
        penalty_amount_usd=30_000_000,
        which_control="sanctions_workflow",
        verified=True,
        is_depository_bank=True,
        note="penalty_amount_usd = OFAC portion; combined OFAC+Fed ≈ $97.8M.",
    ),
    GoldenCase(
        case_id="binance_ofac_2023",
        name="OFAC Settlement with Binance Holdings, Ltd.",
        agency="OFAC (Treasury) + DOJ + FinCEN",
        year=2023,
        citation="Multiple sanctions programs (Iran, Syria, Cuba, Crimea, etc.)",
        primary_source_url="https://ofac.treasury.gov/recent-actions/20231121",
        matter_of_record=(
            "OFAC found Binance matched and executed trades between U.S.-person users and users in "
            "sanctioned jurisdictions/blocked persons (2017–2022); settled for ~$968.6M as part of "
            "a ~$4.3B aggregate resolution."
        ),
        penalty_amount_usd=968_618_825,
        which_control="sanctions_workflow",
        verified=True,
        is_depository_bank=False,
        note="Virtual-currency exchange/MSB, not a depository bank; major OFAC matter of record.",
    ),
    # --- Category D: model risk / algorithmic-model fair lending ---
    GoldenCase(
        case_id="nydfs_apple_card_goldman_2021",
        name="NYDFS Report on the Apple Card Investigation (Goldman Sachs Bank USA)",
        agency="NYDFS",
        year=2021,
        citation="New York fair-lending law",
        primary_source_url="https://www.dfs.ny.gov/system/files/documents/2021/03/rpt_202103_apple_card_investigation.pdf",
        matter_of_record=(
            "After allegations that Apple Card's underwriting algorithm (operated by Goldman Sachs) "
            "discriminated by sex, NYDFS investigated and found no unlawful discrimination under "
            "fair-lending law but cited transparency/customer-service deficiencies."
        ),
        penalty_amount_usd=None,
        which_control="model_risk_management",
        verified=True,
        is_depository_bank=True,
        note="A NO-VIOLATION finding — the closest verifiable public algorithmic-model matter; "
        "clean SR 11-7 model-risk enforcement is supervisory and non-public.",
    ),
)
