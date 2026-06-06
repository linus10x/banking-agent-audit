"""Shared reference implementations of the deployer seams, used across tests.

These are STUBS standing in for the real IdP/KMS and signature-verification
infrastructure a deployer wires. They are deliberately simple but exercise the
exact contracts the primitives enforce.
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from hypothesis import settings

from banking_agent_audit.governance.autonomy_ladder import ControlAttestation
from banking_agent_audit.governance.sovereign_veto import Principal

# A reduced-example profile for fast inner loops (e.g. the mutation pass).
# Activate with HYPOTHESIS_PROFILE=fast.
settings.register_profile("fast", max_examples=20)
settings.register_profile("default", max_examples=settings.default.max_examples)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))


class StubAuthorizer:
    """An :class:`~.sovereign_veto.Authorizer` backed by a credential table."""

    def __init__(
        self,
        credentials: dict[str, Principal],
        allowed_actions: set[str] | None = None,
    ) -> None:
        self._credentials = credentials
        self._allowed = allowed_actions  # None => all actions allowed

    def authenticate(self, credential: str) -> Principal | None:
        return self._credentials.get(credential)

    def authorize(self, principal: Principal, action: str, context: dict[str, Any]) -> bool:
        return self._allowed is None or action in self._allowed


class StubVerifier:
    """An :class:`~.autonomy_ladder.AttestationVerifier`.

    Verifies True only when the attester is in the independent set AND is not the
    requesting agent itself.
    """

    def __init__(self, independent_attesters: set[str]) -> None:
        self._independent = independent_attesters

    def verify(self, attestation: ControlAttestation, requesting_agent_id: str) -> bool:
        if attestation.attester_id == requesting_agent_id:
            return False
        return attestation.attester_id in self._independent


@pytest.fixture
def human_principal() -> Principal:
    return Principal(principal_id="ciso@bank.example", is_agent=False)


@pytest.fixture
def agent_principal() -> Principal:
    return Principal(principal_id="agent-007", is_agent=True)


@pytest.fixture
def authorizer(human_principal: Principal, agent_principal: Principal) -> StubAuthorizer:
    return StubAuthorizer(
        credentials={
            "human-token": human_principal,
            "agent-token": agent_principal,
        },
    )


@pytest.fixture
def restricted_authorizer(human_principal: Principal) -> StubAuthorizer:
    """A human who authenticates but is NOT authorized for the action."""
    return StubAuthorizer(
        credentials={"human-token": human_principal},
        allowed_actions=set(),  # authorizes nothing
    )
