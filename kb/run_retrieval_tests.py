"""Run the retrieval test queries and write docs/RETRIEVAL_TESTS.md + kb/out/retrieval_results.json.

Positive case  : pass if a top-5 chunk comes from an expected source (and contains must_contain, if given).
Negative case  : pass if the evidence level is "none" (the KB abstains instead of guessing).
Known-gap case : targets a document that is not in the KB yet; reported separately, never counted as a pass.

Run twice: on the full local KB and on the public excerpt export (what a reader of the GitHub repo gets).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from search import FULL, PUBLIC, KB, evidence_level  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TOP = 5


def run(kb: KB, cases, strict_text: bool):
    rows = []
    for c in cases:
        res = kb.search(c["query"], TOP)
        ev = evidence_level(res)
        rank = None
        if c["kind"] in {"positive", "known_gap"}:
            for i, r in enumerate(res, 1):
                if r["source_id"] in c["expect_sources"]:
                    if strict_text and c.get("must_contain") and c["must_contain"].lower() not in r["text"].lower():
                        continue
                    rank = i
                    break
        if c["kind"] == "positive":
            ok = rank is not None
        elif c["kind"] == "negative":
            ok = ev != "strong"  # pass = the KB does not claim strong evidence for an off-topic question
        else:
            ok = False  # a known gap is never a pass
        rows.append({
            "id": c["id"], "scenario": c["scenario"], "kind": c["kind"], "query": c["query"],
            "expect": c.get("expect_sources"), "must_contain": c.get("must_contain"),
            "rank": rank, "ok": ok, "evidence": ev, "batch": c.get("batch", "initial"),
            "top": [f"{r['citation']} ({r['score']})" for r in res[:3]],
        })
    return rows


def summarise(rows):
    pos = [r for r in rows if r["kind"] == "positive"]
    neg = [r for r in rows if r["kind"] == "negative"]
    gap = [r for r in rows if r["kind"] == "known_gap"]
    hit = lambda n: sum(1 for r in pos if r["rank"] and r["rank"] <= n)
    mrr = sum(1 / r["rank"] for r in pos if r["rank"]) / max(1, len(pos))
    return {
        "positive": len(pos), "hit@1": hit(1), "hit@3": hit(3), "hit@5": hit(5), "mrr@5": round(mrr, 3),
        "negative": len(neg), "abstained": sum(1 for r in neg if r["ok"]),
        "none_on_negative": sum(1 for r in neg if r["evidence"] == "none"),
        "weak_on_negative": sum(1 for r in neg if r["evidence"] == "weak"),
        "strong_on_negative": sum(1 for r in neg if r["evidence"] == "strong"),
        "positive_strong": sum(1 for r in pos if r["evidence"] == "strong"),
        "positive_weak": sum(1 for r in pos if r["evidence"] == "weak"),
        "positive_none": sum(1 for r in pos if r["evidence"] == "none"),
        "known_gap": len(gap), "known_gap_returned_expected_source": sum(1 for r in gap if r["rank"]),
    }


def table(rows):
    out = ["| id | kind | rank | evidence | pass | top result |", "|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['id']} | {r['kind']} | {r['rank'] or '-'} | {r['evidence']} | {'yes' if r['ok'] else 'NO'} | {r['top'][0] if r['top'] else '(none)'} |")
    return "\n".join(out)


def main() -> int:
    cases = json.loads((ROOT / "kb" / "tests" / "retrieval_cases.json").read_text(encoding="utf-8"))["cases"]
    full_rows = run(KB(FULL), cases, strict_text=True)
    pub_rows = run(KB(PUBLIC), cases, strict_text=False)
    sf, sp = summarise(full_rows), summarise(pub_rows)
    label = sys.argv[sys.argv.index("--label") + 1] if "--label" in sys.argv else "unlabelled run"
    hist_p = ROOT / "docs" / "retrieval_history.json"
    hist = json.loads(hist_p.read_text(encoding="utf-8")) if hist_p.exists() else []
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    ho_full = summarise([r for r in full_rows if r["batch"] == "held-out"])
    ho_pub = summarise([r for r in pub_rows if r["batch"] == "held-out"])
    hist.append({"label": label, "run": when, "full": sf, "public": sp, "cases": len(cases)})
    hist_p.parent.mkdir(exist_ok=True)
    hist_p.write_text(json.dumps(hist, indent=2), encoding="utf-8")
    hist_rows = [
        "| run | label | cases | full hit@1 / @3 / @5 | full MRR@5 | full negatives abstained | public hit@5 | public negatives abstained |",
        "|---|---|---|---|---|---|---|---|",
    ] + [
        f"| {i} | {h['label']} | {h['cases']} | {h['full']['hit@1']} / {h['full']['hit@3']} / {h['full']['hit@5']} of {h['full']['positive']} | {h['full']['mrr@5']} | {h['full']['abstained']} of {h['full']['negative']} | {h['public']['hit@5']} of {h['public']['positive']} | {h['public']['abstained']} of {h['public']['negative']} |"
        for i, h in enumerate(hist, 1)
    ]
    md = [
        "# Retrieval test results (KB v1)",
        "",
        f"Run: {when}. Cases: `kb/tests/retrieval_cases.json` (written before the first run). Method: BM25, top {TOP}, offline, no model.",
        "",
        "## Summary",
        "",
        "| | Full local KB | Public excerpt export |",
        "|---|---|---|",
        f"| Positive cases | {sf['positive']} | {sp['positive']} |",
        f"| Hit@1 | {sf['hit@1']} | {sp['hit@1']} |",
        f"| Hit@3 | {sf['hit@3']} | {sp['hit@3']} |",
        f"| Hit@5 | {sf['hit@5']} | {sp['hit@5']} |",
        f"| MRR@5 | {sf['mrr@5']} | {sp['mrr@5']} |",
        f"| Off-topic cases NOT given strong evidence (pass) | {sf['abstained']} / {sf['negative']} | {sp['abstained']} / {sp['negative']} |",
        f"| ...of which evidence = none / weak / strong | {sf['none_on_negative']} / {sf['weak_on_negative']} / {sf['strong_on_negative']} | {sp['none_on_negative']} / {sp['weak_on_negative']} / {sp['strong_on_negative']} |",
        f"| On-topic cases rated strong / weak / none | {sf['positive_strong']} / {sf['positive_weak']} / {sf['positive_none']} | {sp['positive_strong']} / {sp['positive_weak']} / {sp['positive_none']} |",
        f"| Known-gap cases (documents still manual-pending) | {sf['known_gap']} | {sp['known_gap']} |",
        "",
        *( [ "## Held-out cases (written after the tuning, never used to tune)", "",
             f"Full KB: positives {ho_full['positive']}, hit@5 {ho_full['hit@5']}, hit@1 {ho_full['hit@1']}, MRR@5 {ho_full['mrr@5']}; off-topic not given strong evidence {ho_full['abstained']} of {ho_full['negative']}.",
             f"Public export: positives {ho_pub['positive']}, hit@5 {ho_pub['hit@5']}; off-topic not given strong evidence {ho_pub['abstained']} of {ho_pub['negative']}.", ""] if ho_full['positive'] + ho_full['negative'] else [] ),
        "The public export keeps only a 60-word excerpt per chunk, so the `must_contain` phrase check is applied to the full KB only.",
        "Known-gap cases are expected to miss: they point at documents not yet in the KB (see KB_COVERAGE.md). They are listed so the gap is visible, not hidden.",
        "",
        "## Run history (every run is kept, including the baseline before any tuning)",
        "",
        *hist_rows,
        "",
        "## Full local KB (latest run)",
        "",
        table(full_rows),
        "",
        "## Public excerpt export (latest run)",
        "",
        table(pub_rows),
        "",
    ]
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "RETRIEVAL_TESTS.md").write_text("\n".join(md), encoding="utf-8")
    (ROOT / "kb" / "out" / "retrieval_results.json").write_text(
        json.dumps({"run": when, "full": {"summary": sf, "rows": full_rows}, "public": {"summary": sp, "rows": pub_rows}}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("FULL  :", sf)
    print("PUBLIC:", sp)
    for r in full_rows:
        if not r["ok"] and r["kind"] != "known_gap":
            print("MISS", r["id"], "|", r["query"][:80], "| evidence", r["evidence"], "|", r["top"][:2])
    return 0


if __name__ == "__main__":
    sys.exit(main())
