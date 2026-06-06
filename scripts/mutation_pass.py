#!/usr/bin/env python3
"""Deterministic, committed mutation pass on the security-critical predicates.

Each mutation disables a load-bearing guard in a primitive/control. The suite
MUST kill every mutant (a targeted test must fail with the guard removed). A
surviving mutant means a weak assertion — fix the test, not this script.

This is a focused, reproducible alternative to mutmut/cosmic-ray (which do not
run cleanly on this Python 3.14 layout). Run:

    python scripts/mutation_pass.py

Exit 0 iff every mutant is killed; prints a mutation score.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "banking_agent_audit" / "governance"


@dataclass(frozen=True)
class Mutant:
    name: str
    file: Path
    old: str
    new: str
    killer_test: str  # the test target that must fail when the guard is removed


MUTANTS: tuple[Mutant, ...] = (
    Mutant(
        "P3-disable-prevhash-check",
        SRC / "audit_chain.py",
        "                if event.prev_hash != prev:\n                    return False",
        "                if event.prev_hash != prev:\n                    pass",
        "tests/test_audit_chain.py::test_inplace_prevhash_tamper_detected",
    ),
    Mutant(
        "P3-always-legacy-seed (the original defect)",
        SRC / "audit_chain.py",
        "        if self._deployer_id is not None:\n            return _compute_genesis_hash(self._deployer_id, self._chain_creation_iso)",
        "        if False:\n            return _compute_genesis_hash(self._deployer_id, self._chain_creation_iso)",
        "tests/adversarial/test_al_probes.py::test_al_probe_03a_hardened_chain_does_not_false_tamper",
    ),
    Mutant(
        "P4-disable-onestep-deescalation-guard",
        SRC / "defcon.py",
        "            if self._level - target_level > 1:",
        "            if self._level - target_level > 99:",
        "tests/adversarial/test_al_probes.py::test_al_probe_04_one_call_halt_to_normal_refused",
    ),
    Mutant(
        "P2-allow-agent-self-clear",
        SRC / "sovereign_veto.py",
        '            if principal.is_agent:\n                raise VetoNotAuthorizedError(\n                    "an agent principal may not clear a sovereign veto "',
        '            if False:\n                raise VetoNotAuthorizedError(\n                    "an agent principal may not clear a sovereign veto "',
        "tests/adversarial/test_hardening.py::test_b3b_any_agent_principal_rejected_even_if_different_id",
    ),
    Mutant(
        "P5-allow-self-challenge-by-id",
        SRC / "effective_challenge_harness.py",
        "        if primary_id.strip().casefold() == challenger_id.strip().casefold():",
        "        if False:",
        "tests/adversarial/test_al_probes.py::test_al_probe_05_self_challenge_rejected",
    ),
    Mutant(
        "P1-ignore-missing-controls",
        SRC / "autonomy_ladder.py",
        "        missing = sorted(required - attested)\n        if missing:",
        "        missing = sorted(required - attested)\n        if False:",
        "tests/test_autonomy_ladder.py::test_refuses_promotion_with_missing_controls",
    ),
    Mutant(
        "P5-accept-without-independence",
        SRC / "effective_challenge_harness.py",
        "        if not independent:\n            return Recommendation.ESCALATE",
        "        if False:\n            return Recommendation.ESCALATE",
        "tests/adversarial/test_al_probes.py::test_al_probe_05b_owner_self_challenge_cannot_accept_primary",
    ),
    Mutant(
        "P2-production-self-clear-by-id",
        SRC / "sovereign_veto.py",
        '            if _norm(principal.principal_id) == _norm(self._agent_id):\n                raise VetoNotAuthorizedError("an agent cannot clear its own veto")',
        '            if False:\n                raise VetoNotAuthorizedError("an agent cannot clear its own veto")',
        "tests/adversarial/test_hardening.py::test_b3_production_principal_id_equals_agent_id_rejected",
    ),
    Mutant(
        "B1-allow-non-str-payload-key",
        SRC.parent / "schemas" / "audit_event.py",
        "            if not isinstance(key, str):",
        "            if False:",
        "tests/adversarial/test_hardening.py::test_b1_non_str_dict_key_rejected",
    ),
    Mutant(
        "B2-regen-not-fail-closed",
        SRC / "audit_chain.py",
        "            if not self.verify():  # fail closed: internal consistency is a precondition",
        "            if False:  # fail closed: internal consistency is a precondition",
        "tests/adversarial/test_hardening.py::test_b2_regeneration_guard_fails_closed_on_inconsistency",
    ),
    Mutant(
        "AA-negative-days-not-flagged",
        SRC / "adverse_action_gate.py",
        "        if decision.days_to_notice < 0:",
        "        if False and decision.days_to_notice < 0:",
        "tests/test_adverse_action_gate.py::test_negative_days_to_notice_is_violation",
    ),
    Mutant(
        "MRM-cross-model-report-replay",
        SRC / "model_risk_management.py",
        "        if report.primary_id != model_id:",
        "        if False and report.primary_id != model_id:",
        "tests/adversarial/test_hardening.py::test_r3_mrm_report_must_match_model_id",
    ),
    Mutant(
        "Sanctions-allow-agent-resolver",
        SRC / "sanctions_workflow.py",
        '        if principal.is_agent:\n            raise SanctionsNotAuthorizedError("an agent principal may not resolve a sanctions case")',
        '        if False:\n            raise SanctionsNotAuthorizedError("an agent principal may not resolve a sanctions case")',
        "tests/adversarial/test_hardening.py::test_r3_sanctions_resolution_requires_auth_when_wired",
    ),
)


def _run_test(target: str) -> bool:
    """Return True if the test PASSES (mutant survived), False if it FAILS (killed)."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            target,
            "-x",
            "-q",
            "-p",
            "no:cacheprovider",
            "--no-header",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={"HYPOTHESIS_PROFILE": "fast", "PATH": __import__("os").environ.get("PATH", "")},
    )
    return proc.returncode == 0


def main() -> int:
    killed = 0
    survived: list[str] = []
    for m in MUTANTS:
        original = m.file.read_text()
        if m.old not in original:
            print(f"  SKIP {m.name}: anchor text not found (source drifted)")
            survived.append(m.name + " (anchor-missing)")
            continue
        try:
            m.file.write_text(original.replace(m.old, m.new, 1))
            still_passes = _run_test(m.killer_test)
        finally:
            m.file.write_text(original)  # always restore
        if still_passes:
            print(f"  SURVIVED  {m.name}  (test still passed — weak assertion!)")
            survived.append(m.name)
        else:
            print(f"  killed    {m.name}")
            killed += 1

    total = len(MUTANTS)
    score = killed / total * 100
    print(f"\nMutation score: {killed}/{total} killed ({score:.0f}%)")
    if survived:
        print("Survivors:", ", ".join(survived))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
