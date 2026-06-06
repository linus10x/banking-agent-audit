"""Minimal CLI: print the claim sheet and verify a JSONL audit ledger.

banking-audit claims            # print the obligation claim sheet
banking-audit verify <ledger>   # verify a JSONL audit chain (legacy seed)
"""

from __future__ import annotations

import sys
from pathlib import Path

from banking_agent_audit import __version__
from banking_agent_audit.governance.audit_chain import AuditChain
from banking_agent_audit.obligation_map import OBLIGATIONS


def _print_claims() -> int:
    print(f"banking-agent-audit {__version__} — obligation claim sheet\n")
    for ob in OBLIGATIONS:
        mark = "" if ob.verified else "  [UNVERIFIED]"
        print(f"- [{ob.claim_layer.value}] {ob.title}{mark}")
        print(f"    {ob.citation}")
    return 0


def _verify(path_str: str) -> int:
    path = Path(path_str)
    if not path.exists():
        print(f"ledger not found: {path}", file=sys.stderr)
        return 2
    chain = AuditChain(log_file=path)
    ok = chain.verify()
    print(f"{path}: {'VERIFIED' if ok else 'TAMPER DETECTED'} ({len(chain)} events)")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args[0] == "claims":
        return _print_claims()
    if args[0] == "verify" and len(args) == 2:
        return _verify(args[1])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
