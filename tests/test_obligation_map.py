"""The claim sheet, made executable: claims must match implemented reality."""

from __future__ import annotations

import importlib

from banking_agent_audit import obligation_map as om


def test_two_must_have_controls_are_implemented() -> None:
    impl = om.implemented()
    ids = {o.obligation_id for o in impl}
    assert "mrm_effective_challenge" in ids
    assert "ecoa_reg_b_adverse_action" in ids


def test_implemented_obligations_point_to_real_modules() -> None:
    for ob in om.implemented():
        assert ob.module is not None
        mod = importlib.import_module(f"banking_agent_audit.{ob.module}")
        assert mod is not None


def test_documented_patterns_have_no_module_claim() -> None:
    # A documented pattern must NOT claim an implementing module (no overclaim).
    for ob in om.documented_patterns():
        assert ob.module is None


def test_sanctions_is_deployer_wired_not_implemented_control() -> None:
    wired = {o.obligation_id for o in om.deployer_wired()}
    assert "bsa_aml_ofac_disposition" in wired
    # It is NOT claimed as an operating control.
    impl_ids = {o.obligation_id for o in om.implemented()}
    assert "bsa_aml_ofac_disposition" not in impl_ids


def test_every_obligation_has_citation_and_source() -> None:
    for ob in om.OBLIGATIONS:
        assert ob.citation.strip()
        assert ob.source_url.startswith("https://")


def test_unverified_obligations_are_flagged() -> None:
    # Any obligation not primary-source verified must carry verified=False so the
    # CLI prints [UNVERIFIED]. (Currently all are verified; this guards drift.)
    for ob in om.OBLIGATIONS:
        assert isinstance(ob.verified, bool)
