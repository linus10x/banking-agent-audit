"""P3 — hash-chain ledger tests (unit + property)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from banking_agent_audit.governance.audit_chain import (
    GENESIS_HASH,
    AuditChain,
    AuditChainTamperError,
    InMemoryWitnessRegister,
    _compute_genesis_hash,
)
from banking_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel

ET = AuditEventType.AGENT_ACTION
AL = AutonomyLevel.A2_DELEGATED


def _append_n(chain: AuditChain, n: int) -> None:
    for i in range(n):
        chain.append(ET, AL, f"agent-{i}", {"i": i})


# -- the corrected genesis-seed branch -----------------------------------


def test_legacy_chain_seeds_zero_seed_and_verifies() -> None:
    chain = AuditChain()  # deployer_id=None => legacy
    assert chain.genesis_seed() == GENESIS_HASH
    _append_n(chain, 5)
    assert chain.verify() is True
    chain.verify_strict()  # does not raise


def test_hardened_chain_seeds_deployer_key_and_verifies() -> None:
    chain = AuditChain(deployer_id="bank-x", chain_creation_iso="2026-06-05T00:00:00+00:00")
    expected = _compute_genesis_hash("bank-x", "2026-06-05T00:00:00+00:00")
    assert chain.genesis_seed() == expected
    assert chain.genesis_seed() != GENESIS_HASH
    _append_n(chain, 5)
    # The corrected behavior: a clean hardened chain verifies True (no false TAMPER).
    assert chain.verify() is True
    chain.verify_strict()


def test_hardened_first_event_prev_hash_is_deployer_seed() -> None:
    chain = AuditChain(deployer_id="bank-x")
    ev = chain.append(ET, AL, "agent", {})
    assert ev.prev_hash == chain.genesis_seed()
    assert ev.prev_hash != GENESIS_HASH


def test_two_deployers_seeds_differ() -> None:
    a = AuditChain(deployer_id="bank-a", chain_creation_iso="t")
    b = AuditChain(deployer_id="bank-b", chain_creation_iso="t")
    assert a.genesis_seed() != b.genesis_seed()


def test_empty_chain_head_is_genesis_seed() -> None:
    legacy = AuditChain()
    assert legacy.chain_head() == GENESIS_HASH
    hardened = AuditChain(deployer_id="bank-x")
    assert hardened.chain_head() == hardened.genesis_seed()


# -- tamper detection -----------------------------------------------------


def test_inplace_payload_tamper_detected() -> None:
    chain = AuditChain(deployer_id="bank-x")
    _append_n(chain, 3)
    # Mutate a stored event's payload without recomputing the hash.
    chain._store[1] = replace(chain._store[1], payload={"i": 999})
    assert chain.verify() is False
    with pytest.raises(AuditChainTamperError):
        chain.verify_strict()


def test_inplace_prevhash_tamper_detected() -> None:
    chain = AuditChain()
    _append_n(chain, 3)
    chain._store[2] = replace(chain._store[2], prev_hash="deadbeef" * 8).with_hash()
    assert chain.verify() is False
    with pytest.raises(AuditChainTamperError):
        chain.verify_strict()


def test_persistence_roundtrip(tmp_path: Path) -> None:
    log = tmp_path / "audit.jsonl"
    chain = AuditChain(log_file=log, deployer_id="bank-x", chain_creation_iso="t")
    _append_n(chain, 4)
    # Reload from disk with the SAME deployer params: must verify.
    reloaded = AuditChain(log_file=log, deployer_id="bank-x", chain_creation_iso="t")
    assert len(reloaded) == 4
    assert reloaded.verify() is True
    # On-disk lines are valid JSON.
    lines = [json_line for json_line in log.read_text().splitlines() if json_line]
    assert all(json.loads(line)["event_hash"] for line in lines)


# -- production mode + witness anchoring ---------------------------------


def test_production_mode_requires_witness() -> None:
    with pytest.raises(ValueError, match="witness"):
        AuditChain(mode="production")  # no witness => fail closed


def test_production_mode_starts_with_witness() -> None:
    chain = AuditChain(
        mode="production",
        witness_register=InMemoryWitnessRegister(),
        deployer_id="bank-x",
    )
    assert chain.mode == "production"


def test_production_mode_requires_deployer_id() -> None:
    with pytest.raises(ValueError, match="deployer_id"):
        AuditChain(mode="production", witness_register=InMemoryWitnessRegister())


def test_invalid_mode_rejected() -> None:
    with pytest.raises(ValueError, match="mode"):
        AuditChain(mode="bogus")


def test_anchor_records_witness_event() -> None:
    witness = InMemoryWitnessRegister()
    chain = AuditChain(deployer_id="bank-x", witness_register=witness)
    _append_n(chain, 2)
    receipt = chain.anchor_to_witness()
    assert receipt["head_hash"] in witness.anchored_heads()
    # The anchor itself is chained.
    assert chain.events()[-1].event_type is AuditEventType.WITNESS_ANCHOR
    assert chain.verify() is True


def test_anchor_without_witness_raises() -> None:
    chain = AuditChain()
    with pytest.raises(ValueError, match="witness"):
        chain.anchor_to_witness()


# -- the regeneration attack (end-to-end rebuild) ------------------------


def test_regeneration_detected_via_witness() -> None:
    witness = InMemoryWitnessRegister()
    chain = AuditChain(deployer_id="bank-x", witness_register=witness)
    _append_n(chain, 3)
    chain.anchor_to_witness()  # anchors the real head externally
    anchored = witness.anchored_heads()[0]

    # Attacker regenerates the ENTIRE chain from scratch (internally consistent).
    regen = AuditChain(deployer_id="bank-x", witness_register=witness)
    _append_n(regen, 3)  # different events => different heads
    # In-place verify passes (chain is internally consistent)...
    assert regen.verify() is True
    # ...but the externally-anchored head is absent => regeneration detected.
    assert anchored not in {e.event_hash for e in regen.events()}
    assert regen.verify_regeneration_resistant() is False


def test_regeneration_resistant_true_for_genuine_chain() -> None:
    witness = InMemoryWitnessRegister()
    chain = AuditChain(deployer_id="bank-x", witness_register=witness)
    _append_n(chain, 2)
    chain.anchor_to_witness()
    _append_n(chain, 2)
    assert chain.verify_regeneration_resistant() is True


def test_regeneration_check_without_witness_raises() -> None:
    chain = AuditChain()
    with pytest.raises(ValueError, match="witness"):
        chain.verify_regeneration_resistant()


# -- property: clean chains of any size always verify --------------------


@settings(max_examples=2000, deadline=None)
@given(
    n=st.integers(min_value=0, max_value=60),
    deployer=st.one_of(st.none(), st.text(min_size=1, max_size=20)),
)
def test_property_clean_chain_always_verifies(n: int, deployer: str | None) -> None:
    chain = AuditChain(deployer_id=deployer, chain_creation_iso="fixed")
    _append_n(chain, n)
    assert chain.verify() is True
    chain.verify_strict()
    # Head linkage invariant: each event's prev_hash == prior event_hash.
    prev = chain.genesis_seed()
    for ev in chain.events():
        assert ev.prev_hash == prev
        prev = ev.event_hash


@settings(max_examples=2000, deadline=None)
@given(
    n=st.integers(min_value=1, max_value=40),
    idx_seed=st.integers(min_value=0, max_value=10_000),
)
def test_property_any_single_payload_mutation_detected(n: int, idx_seed: int) -> None:
    chain = AuditChain(deployer_id="bank-x")
    _append_n(chain, n)
    idx = idx_seed % n
    chain._store[idx] = replace(chain._store[idx], payload={"tampered": True})
    assert chain.verify() is False
