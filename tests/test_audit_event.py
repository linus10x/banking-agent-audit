"""Schema tests for AuditEvent + enums."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from banking_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)


def _make(payload: dict[str, object]) -> AuditEvent:
    return AuditEvent(
        sequence=0,
        event_type=AuditEventType.AGENT_ACTION,
        autonomy_level=AutonomyLevel.A1_ASSISTED,
        agent_id="a",
        payload=payload,
        timestamp="t",
        prev_hash="0" * 64,
    ).with_hash()


def test_autonomy_level_rank_monotonic() -> None:
    ranks = [lvl.rank for lvl in AutonomyLevel]
    assert ranks == [0, 1, 2, 3, 4]


def test_autonomy_level_can_write() -> None:
    assert AutonomyLevel.A0_INFORMATIONAL.can_write is False
    assert all(lvl.can_write for lvl in AutonomyLevel if lvl is not AutonomyLevel.A0_INFORMATIONAL)


def test_requires_human_approval() -> None:
    assert AutonomyLevel.A0_INFORMATIONAL.requires_human_approval is True
    assert AutonomyLevel.A1_ASSISTED.requires_human_approval is True
    assert AutonomyLevel.A2_DELEGATED.requires_human_approval is False


def test_hash_excludes_itself_and_is_reproducible() -> None:
    ev = _make({"x": 1})
    assert ev.event_hash == ev.compute_hash()
    # Recomputing from a copy with a wiped hash reproduces the same value.
    from dataclasses import replace

    assert replace(ev, event_hash="").compute_hash() == ev.event_hash


def test_to_from_dict_roundtrip() -> None:
    ev = _make({"x": 1, "y": "two"})
    again = AuditEvent.from_dict(ev.to_dict())
    assert again == ev
    assert again.compute_hash() == ev.event_hash


@settings(max_examples=1000)
@given(
    payload=st.dictionaries(
        st.text(min_size=1, max_size=8),
        st.one_of(st.integers(), st.text(max_size=8), st.booleans()),
        max_size=6,
    )
)
def test_property_hash_deterministic(payload: dict[str, object]) -> None:
    a = _make(dict(payload))
    b = _make(dict(payload))
    assert a.event_hash == b.event_hash
