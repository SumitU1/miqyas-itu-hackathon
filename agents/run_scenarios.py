"""Run scenarios end to end and write, per scenario, into <out>/<id>/:
audit.jsonl (hash-chained), trace.md (why each decision was made), decisions.json, summary.json.

    python -m agents.run_scenarios scenarios/S3_clinic_record_sharing.json --out runs/2026-10-28
    python -m agents.run_scenarios --all --out runs/2026-10-28 --jobs 4 --workers 4

--workers N: model calls in flight inside one scenario (1 = one at a time); --jobs N: scenarios run side by side.
Exit code 0 = every audit chain verified, 1 = a chain failed, 2 = could not start (usage, key, missing file).

Model: an OpenAI-compatible gateway, alias `auto`. The key comes from GATEWAY_LLM_KEY or from the .env
file named in GATEWAY_ENV_FILE; it is never printed or logged.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .audit import AuditLog, read_log_lines, verify_file
from .coordinator import Coordinator
from .kbtool import KBTool, load_kb
from .llm import DEFAULT_URL, ModelClient, load_key
from .scenario import validate_scenario
from .trace import build_trace

ROOT = Path(__file__).resolve().parent.parent


def summarise(decisions, audit_path, scen) -> dict:
    recs = [json.loads(l) for l in read_log_lines(audit_path) if l.strip()]
    answers = [a for d in decisions for a in d["adviser_answers"]]
    calls = [r["payload"] for r in recs if r["type"] == "model_call"]
    ok, info = verify_file(audit_path)
    return {
        "scenario_id": scen["scenario_id"], "title": scen["title"], "synthetic": scen["synthetic"],
        "decisions": len(decisions), "needs_human": sum(d["needs_human"] for d in decisions),
        "approvals_simulated": sum(1 for d in decisions if d["approval"].get("simulated")),
        "adviser_questions": len(answers), "adviser_rulings": sum(a["outcome"] == "ruling" for a in answers),
        "adviser_abstentions": dict(collections.Counter(a["abstain_reason"] for a in answers if a["outcome"] == "abstain")),
        "adviser_evidence": dict(collections.Counter(a["evidence"] for a in answers)),
        "conflicts": dict(collections.Counter(c["type"] for d in decisions for c in d["conflicts"])),
        "citation_violations": sum(len(a["citation_violations"]) for d in decisions for a in d["assessments"]),
        "assessment_failures": sum(1 for d in decisions for a in d["assessments"] if a["status"] == "model_unavailable"),
        "emergency_shortcuts": sum(1 for d in decisions for a in d["assessments"] if a["status"] == "emergency"),
        "guard_events": sum(1 for r in recs if r["type"] == "guard"),
        "kb_queries": sum(1 for r in recs if r["type"] == "kb_query"),
        "model_calls": len(calls), "model_calls_failed": sum(1 for c in calls if not c["ok"]),
        "served_models": sorted({c["served_model"] for c in calls if c.get("served_model")}),
        "model_alias": "auto", "kb_build_id": decisions[0]["kb_build_id"] if decisions else None,
        "audit_records": info.get("records"), "head_hash": info.get("head"), "chain_verified": ok,
        "run_finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def run_scenario_file(path, out_root, make_model, plan_queries: bool = False, workers: int = 4, kb_index=None) -> dict:
    scen = json.loads(Path(path).read_text(encoding="utf-8"))
    errs = validate_scenario(scen)
    if errs:
        raise ValueError(f"{path}: {errs}")
    out = Path(out_root) / scen["scenario_id"]
    out.mkdir(parents=True, exist_ok=True)
    log = out / "audit.jsonl"
    if log.exists():                                        # never overwrite evidence: keep the earlier log aside
        stamp = time.strftime("%Y%m%dT%H%M%S")
        aside = out / f"audit.{stamp}.previous.jsonl"
        n = 1
        while aside.exists():                               # two runs in one second must not clobber or crash
            n += 1
            aside = out / f"audit.{stamp}-{n}.previous.jsonl"
        log.rename(aside)
    audit = AuditLog(log, run_id=scen["scenario_id"])
    kb = KBTool(kb_index or load_kb(), audit)
    decisions = Coordinator(kb, make_model(audit), audit, plan_queries=plan_queries, workers=workers).run_scenario(scen)
    summary = summarise(decisions, log, scen)
    (out / "decisions.json").write_text(json.dumps(decisions, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "trace.md").write_text(build_trace(log, kb), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def main(argv=None, model_factory=None) -> int:
    """model_factory(audit) -> model; the default talks to the gateway. Tests pass a scripted one."""
    if hasattr(sys.stdout, "reconfigure"):                  # absent when output is redirected to a StringIO
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("scenarios", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "runs" / time.strftime("%Y-%m-%d")))
    ap.add_argument("--workers", type=int, default=4, help="model calls in flight inside one scenario")
    ap.add_argument("--jobs", type=int, default=1, help="scenarios run side by side")
    a = ap.parse_args(argv)
    if not a.all and not a.scenarios:
        print("nothing to run: name one or more scenario files, or pass --all", file=sys.stderr)
        return 2
    files = sorted((ROOT / "scenarios").glob("S*.json")) if a.all else [Path(p) for p in a.scenarios]
    missing = [str(f) for f in files if not f.exists()]
    if missing:
        print(f"scenario file not found: {', '.join(missing)}", file=sys.stderr)
        return 2
    if model_factory is None:
        env = dict(os.environ)
        try:
            key = load_key(env)
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            return 2
        url = env.get("GATEWAY_URL", DEFAULT_URL)
        model_factory = lambda audit: ModelClient(url, key, audit)
    kb_index = load_kb()                                    # read-only index, shared by every scenario

    def one(f):
        t = time.time()
        try:
            return run_scenario_file(f, a.out, model_factory, plan_queries=True, workers=a.workers, kb_index=kb_index), time.time() - t
        except Exception as e:                              # one bad scenario must not hide the others' results
            return {"failed_file": str(f), "error": f"{type(e).__name__}: {e}"}, time.time() - t

    with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as pool:
        results = list(pool.map(one, files))                # printed in file order whatever order they finished in
    rc = 0
    for s, secs in results:
        if "failed_file" in s:
            print(f"{Path(s['failed_file']).name}: FAILED, {s['error']}")
            rc = 1
            continue
        print(f"{s['scenario_id']}: {s['decisions']} decisions, {s['needs_human']} need a human, adviser "
              f"{s['adviser_rulings']}/{s['adviser_questions']} rulings, abstentions {s['adviser_abstentions']}, "
              f"{s['model_calls']} model calls ({s['model_calls_failed']} failed), chain verified: {s['chain_verified']}, {secs:.0f}s")
        rc |= 0 if s["chain_verified"] else 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
