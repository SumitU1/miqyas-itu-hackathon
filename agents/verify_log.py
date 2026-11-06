"""Check an audit log's hash chain.

    python -m agents.verify_log runs/2026-10-28/S2/audit.jsonl
    python -m agents.verify_log runs/2026-10-28/S2/audit.jsonl --head <head_hash from summary.json>

Exit code 0 = chain intact; 1 = broken, unreadable content, or no records; 2 = no such file (or usage error).
Without --head a cut-off tail cannot be seen; with the head hash published elsewhere (summary.json, the
report) it can.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .audit import verify_file


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check an audit log's hash chain.")
    ap.add_argument("log", help="path to an audit.jsonl file")
    ap.add_argument("--head", default=None, help="expected head hash (detects removed records at the end)")
    a = ap.parse_args(argv)
    if not Path(a.log).is_file():
        print(f"cannot verify {a.log}: {'it is a directory' if Path(a.log).is_dir() else 'no such file'}", file=sys.stderr)
        return 2
    ok, info = verify_file(a.log, expected_head=a.head)
    if ok and info["records"] == 0:
        print(f"no records found in {a.log}: nothing to verify")
        return 1
    if a.head is None:
        print("note: without --head a cut-off tail cannot be detected", file=sys.stderr)
    if ok:
        print(f"chain verified: {info['records']} records, head {info['head']}")
        return 0
    print(f"chain FAILS at record {info['bad_seq']}: {info['reason']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
