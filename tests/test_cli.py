"""CLI tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from banking_agent_audit.cli import main
from banking_agent_audit.governance.audit_chain import AuditChain
from banking_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel


def test_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "claim sheet" in capsys.readouterr().out


def test_claims(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["claims"]) == 0
    out = capsys.readouterr().out
    assert "implemented_control" in out
    assert "deployer_wired" in out


def test_verify_clean_ledger(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = tmp_path / "audit.jsonl"
    chain = AuditChain(log_file=log)  # legacy seed (CLI verifies legacy)
    chain.append(AuditEventType.AGENT_ACTION, AutonomyLevel.A1_ASSISTED, "a", {"x": 1})
    assert main(["verify", str(log)]) == 0
    assert "VERIFIED" in capsys.readouterr().out


def test_verify_missing_ledger() -> None:
    assert main(["verify", "/nonexistent/path.jsonl"]) == 2


def test_unknown_command() -> None:
    assert main(["frobnicate"]) == 2
