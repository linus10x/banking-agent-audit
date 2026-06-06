"""P5 — effective-challenge harness tests."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from banking_agent_audit.governance.audit_chain import AuditChain
from banking_agent_audit.governance.effective_challenge_harness import (
    EffectiveChallengeHarness,
    IndependenceAttestation,
    Recommendation,
)


def _independent(chosen_by: str = "mrm-lead") -> IndependenceAttestation:
    return IndependenceAttestation(
        chosen_by=chosen_by,
        same_owner=False,
        same_vendor_family=False,
        same_prompt_template=False,
        statement="distinct vendor, distinct team",
    )


def _not_independent() -> IndependenceAttestation:
    return IndependenceAttestation(
        chosen_by="model-owner",
        same_owner=True,
        same_vendor_family=True,
        same_prompt_template=True,
    )


EVAL = [(1, 1), (2, 2), (3, 3), (4, 4)]


def test_self_challenge_rejected_by_id() -> None:
    with pytest.raises(ValueError, match="self-challenge"):
        EffectiveChallengeHarness(
            primary_model=lambda x: x,
            challenger_model=lambda x: x,  # different object but...
            eval_set=EVAL,
            independence=_independent(),
            primary_id="m1",
            challenger_id="m1",  # same id
        )


def test_self_challenge_rejected_by_callable_identity() -> None:
    fn = lambda x: x  # noqa: E731
    with pytest.raises(ValueError, match="same callable"):
        EffectiveChallengeHarness(
            primary_model=fn,
            challenger_model=fn,
            eval_set=EVAL,
            independence=_independent(),
            primary_id="m1",
            challenger_id="m2",
        )


def test_empty_eval_set_rejected() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        EffectiveChallengeHarness(
            primary_model=lambda x: x,
            challenger_model=lambda x: -x,
            eval_set=[],
            independence=_independent(),
            primary_id="m1",
            challenger_id="m2",
        )


def test_bad_thresholds_rejected() -> None:
    with pytest.raises(ValueError, match="threshold"):
        EffectiveChallengeHarness(
            primary_model=lambda x: x,
            challenger_model=lambda x: -x,
            eval_set=EVAL,
            independence=_independent(),
            primary_id="m1",
            challenger_id="m2",
            accept_threshold=0.5,
            investigate_threshold=0.3,
        )


def test_independent_agreement_accepts_primary() -> None:
    h = EffectiveChallengeHarness(
        primary_model=lambda x: x,
        challenger_model=lambda x: x,
        eval_set=EVAL,
        independence=_independent(),
        primary_id="m1",
        challenger_id="m2",
    )
    report = h.run()
    assert report.disagreement_rate == 0.0
    assert report.recommendation is Recommendation.ACCEPT_PRIMARY
    assert report.independent is True


def test_owner_self_challenge_cannot_accept_primary() -> None:
    # Models agree perfectly, but independence is NOT attested => escalate.
    h = EffectiveChallengeHarness(
        primary_model=lambda x: x,
        challenger_model=lambda x: x,
        eval_set=EVAL,
        independence=_not_independent(),
        primary_id="m1",
        challenger_id="m2",
    )
    report = h.run()
    assert report.disagreement_rate == 0.0
    assert report.independent is False
    assert report.recommendation is Recommendation.ESCALATE


def test_high_disagreement_escalates() -> None:
    h = EffectiveChallengeHarness(
        primary_model=lambda x: x,
        challenger_model=lambda x: -x,  # always disagrees
        eval_set=EVAL,
        independence=_independent(),
        primary_id="m1",
        challenger_id="m2",
    )
    report = h.run()
    assert report.disagreement_rate == 1.0
    assert report.recommendation is Recommendation.ESCALATE


def test_mid_disagreement_investigates() -> None:
    # 1 of 4 disagrees => 0.25 in (0.05, 0.30] => INVESTIGATE.
    def challenger(x: int) -> int:
        return 0 if x == 1 else x

    h = EffectiveChallengeHarness(
        primary_model=lambda x: x,
        challenger_model=challenger,
        eval_set=EVAL,
        independence=_independent(),
        primary_id="m1",
        challenger_id="m2",
    )
    report = h.run()
    assert report.disagreement_rate == 0.25
    assert report.recommendation is Recommendation.INVESTIGATE


def test_run_records_to_chain_with_attestation() -> None:
    chain = AuditChain(deployer_id="bank-x")
    h = EffectiveChallengeHarness(
        primary_model=lambda x: x,
        challenger_model=lambda x: x,
        eval_set=EVAL,
        independence=_independent("mrm-lead"),
        primary_id="m1",
        challenger_id="m2",
        audit_chain=chain,
    )
    h.run()
    ev = chain.events()[-1]
    assert ev.event_type.value == "model_validated"
    assert ev.payload["independence_attestation"]["chosen_by"] == "mrm-lead"
    assert chain.verify() is True


def test_eval_set_hash_stable() -> None:
    h = EffectiveChallengeHarness(
        primary_model=lambda x: x,
        challenger_model=lambda x: -x,
        eval_set=EVAL,
        independence=_independent(),
        primary_id="m1",
        challenger_id="m2",
    )
    assert h.run().eval_set_hash == h.run().eval_set_hash


@settings(max_examples=1000)
@given(disagree_count=st.integers(min_value=0, max_value=10))
def test_property_no_independence_never_accepts(disagree_count: int) -> None:
    eval_set = [(i, i) for i in range(10)]

    def challenger(x: int) -> int:
        return -1 if x < disagree_count else x

    h = EffectiveChallengeHarness(
        primary_model=lambda x: x,
        challenger_model=challenger,
        eval_set=eval_set,
        independence=_not_independent(),
        primary_id="m1",
        challenger_id="m2",
    )
    assert h.run().recommendation is not Recommendation.ACCEPT_PRIMARY
