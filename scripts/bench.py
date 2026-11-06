"""Reproducible before/after benchmark. No network, no real model.

    python scripts/bench.py --out docs/bench/before.json --golden docs/bench/golden_retrieval.json
    python scripts/bench.py --out docs/bench/after.json  --compare docs/bench/golden_retrieval.json

Measures
  kb_load_ms           time to construct the KB index from kb/out/chunks.jsonl (median of 5)
  kb_load_peak_mb      peak Python memory while doing it (tracemalloc)
  query_ms_mean / p95  per-query search latency over every retrieval test query (best of 5 passes)
  scenario_wall_s      wall clock of scenario S2 end to end with a scripted model that sleeps
                       MODEL_LATENCY_S per call (stands in for gateway latency; the real gateway took 4-8 s per call)
  scenario_model_calls number of model calls in that run (so a speed-up is not just fewer calls)
--golden writes every query's ranked (chunk id, score, coverage, evidence); --compare fails if any differs.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "kb"))

import search  # noqa: E402

MODEL_LATENCY_S = 0.25


def queries():
    cases = json.loads((ROOT / "kb" / "tests" / "retrieval_cases.json").read_text(encoding="utf-8"))["cases"]
    return [c["query"] for c in cases]


def bench_kb():
    loads = []
    for _ in range(5):
        t = time.perf_counter()
        kb = search.KB()
        loads.append((time.perf_counter() - t) * 1000)
    tracemalloc.start()
    search.KB()
    peak = tracemalloc.get_traced_memory()[1] / 1e6
    tracemalloc.stop()
    qs = queries()
    best = None
    for _ in range(5):
        per = []
        for q in qs:
            t = time.perf_counter()
            kb.search(q, k=5)
            per.append((time.perf_counter() - t) * 1000)
        if best is None or sum(per) < sum(best):
            best = per
    best.sort()
    return kb, {"kb_load_ms": round(statistics.median(loads), 1), "kb_load_peak_mb": round(peak, 1), "queries": len(qs),
                "query_ms_mean": round(statistics.mean(best), 3), "query_ms_p95": round(best[int(len(best) * 0.95) - 1], 3)}


def golden(kb):
    out = {}
    for q in queries():
        res = kb.search(q, k=5)
        out[q] = {"evidence": search.evidence_level(res), "top": [[c["chunk_id"], c["score"], c["coverage"]] for c in res]}
    return out


def compare_golden(want, got):
    """Queries whose retrieval differs. An empty saved file, or a query on only one side, counts as a difference."""
    if not want:
        return ["<empty golden file>"]
    return sorted(q for q in set(want) | set(got) if want.get(q) != got.get(q))


def bench_scenario(workers):
    from agents.audit import AuditLog
    from agents.coordinator import Coordinator
    from agents.kbtool import KBTool
    from agents.testing import ScriptedModel
    from agents.tests.test_coordinator import by_actor

    inner = by_actor({})

    def base(actor, system, user):
        if actor == "agent:adviser" and "PASSAGES" not in user:     # the query-planning call
            return {"queries": ["patient consent sharing health information facility", "health data stored outside the State"]}
        return inner(actor, system, user)

    with tempfile.TemporaryDirectory() as d:
        audit = AuditLog(Path(d) / "a.jsonl", "bench")
        kb = KBTool(search.KB(), audit)
        model = ScriptedModel(base, latency=MODEL_LATENCY_S)
        scen = json.loads((ROOT / "scenarios" / "S2_wearable_localisation.json").read_text(encoding="utf-8"))
        t = time.perf_counter()
        Coordinator(kb, model, audit, plan_queries=True, workers=workers).run_scenario(scen)
        wall = time.perf_counter() - t
        from agents.audit import verify_file
        ok, _ = verify_file(Path(d) / "a.jsonl")
    return {"scenario_wall_s": round(wall, 2), "scenario_model_calls": model.calls, "scenario_chain_ok": ok,
            "model_latency_s": MODEL_LATENCY_S, "workers": workers}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--golden")
    ap.add_argument("--compare")
    ap.add_argument("--workers", type=int, default=4, help="1 reproduces the sequential baseline")
    a = ap.parse_args()
    kb, res = bench_kb()
    res.update(bench_scenario(a.workers))
    rc = 0
    if a.golden:
        Path(a.golden).parent.mkdir(parents=True, exist_ok=True)
        Path(a.golden).write_text(json.dumps(golden(kb), indent=1, ensure_ascii=False), encoding="utf-8")
    if a.compare:
        want, got = json.loads(Path(a.compare).read_text(encoding="utf-8")), golden(kb)
        diff = compare_golden(want, got)
        res["retrieval_identical_to_golden"] = not diff
        if diff:
            rc = 1
            print("RETRIEVAL DIFFERS for", len(diff), "queries, first:", diff[0])
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    return rc


if __name__ == "__main__":
    sys.exit(main())
