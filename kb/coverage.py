"""Coverage check: KB v1 against the source list, the plan's required document families, and integrity rules.

Writes docs/KB_COVERAGE.md and kb/out/coverage.json. Exit code 1 if any integrity check fails.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "kb"))

# What the ITU hackathon plan (26 Oct 2026) says the KB must cover, mapped to registry ids.
REQUIRED = [
    ("DHA rules (Dubai health regulator)", ["DHA-AI-2021", "DHA-TELEHEALTH-STD-V4", "DHA-TELEHEALTH-POL-2021", "DHA-HIS-2024", "DHA-MEDAD-2022"]),
    ("MOHAP rules (federal health ministry)", ["MOHAP-MD51-2021", "MOHAP-HEALTHAD-GUIDE", "MOHAP-PROMO-CODE-2017"]),
    ("DoH rules (Abu Dhabi health regulator)", ["DOH-AI-2018", "DOH-HIE-2020", "DOH-ADHICS-V2"]),
    ("TDRA device rules", ["TDRA-TAR-POLICY-V3", "TDRA-TAR-REG-V3", "TDRA-IOT-PROC-V1"]),
    ("PDPL (personal data protection law)", ["UAE-PDPL-2021"]),
    ("Federal Law 2/2019 on ICT in health (+ executive regulations)", ["UAE-FL2-2019", "UAE-CR32-2020"]),
    ("Medical-product decree (Federal Decree-Law 38/2024)", ["UAE-FDL38-2024"]),
    ("Advertising rules", ["NMC-AD-GUIDE", "DHA-MEDAD-2022", "MOHAP-HEALTHAD-GUIDE", "UAE-FL15-2020"]),
    ("AI-ethics and AI policy", ["UAE-AI-CHARTER-2024", "UAE-AI-STRATEGY-2031", "DUBAI-AI-ETHICS-2022", "DHA-AI-2021", "DOH-AI-2018"]),
    ("Standards: ITU-T Y.3172 and AI Readiness Framework 2.0", ["ITU-Y3172", "ITU-AIREADY-2"]),
    ("Extra (not in the plan): medical liability, global health-AI ethics", ["UAE-FDL4-2016", "WHO-AI-HEALTH-2021"]),
]
REQUIRED_FIELDS = ["chunk_id", "source_id", "text", "citation", "locator", "url", "title", "issuer", "doc_date",
                   "version_status", "redistribute", "review_status", "clinical_review", "source_file_sha256", "text_sha256"]


def union_len(ranges):
    pts = sorted(set(p for a, b in ranges for p in range(a, b + 1)))
    return len(pts)


def main() -> int:
    reg = json.loads((ROOT / "sources" / "sources.json").read_text(encoding="utf-8"))["sources"]
    chunks = [json.loads(l) for l in (ROOT / "kb" / "out" / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    public = [json.loads(l) for l in (ROOT / "kb" / "out" / "public" / "chunks_public.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    report = json.loads((ROOT / "kb" / "out" / "build_report.json").read_text(encoding="utf-8"))
    manifest_p = ROOT / "kb" / "raw" / "MANIFEST.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8")) if manifest_p.exists() else {}
    by_src: dict[str, list] = {}
    for c in chunks:
        by_src.setdefault(c["source_id"], []).append(c)
    ids = {s["id"] for s in reg}

    rows, status = [], {}
    for s in reg:
        cs = by_src.get(s["id"], [])
        rep = report["sources"][s["id"]]
        ingested = bool(cs)
        status[s["id"]] = ingested
        pages = [(c["page_start"], c["page_end"]) for c in cs if c["page_start"] is not None]
        span = s.get("pages")
        expected = (span[1] - span[0] + 1) if span else None
        covered = union_len(pages) if pages else None
        rows.append({
            "id": s["id"], "ingested": ingested, "method": s["fetch"]["method"], "chunks": len(cs),
            "words": sum(c["n_words"] for c in cs), "pages_covered": covered, "pages_expected": expected,
            "empty_pages": rep["empty_pages"], "kind": s["kind"], "jurisdiction": s["jurisdiction"],
            "version_status": s["version_status"],
            "partial": "PARTIAL" in s["title"] or "brief only" in s["title"],
        })

    # ---- integrity checks
    checks = []

    def check(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    missing = [(c["chunk_id"], f) for c in chunks for f in REQUIRED_FIELDS if c.get(f) in (None, "")]
    check("every chunk carries all citation fields", not missing, f"{len(missing)} missing" if missing else f"{len(chunks)} chunks checked")
    check("chunk ids are unique", len({c["chunk_id"] for c in chunks}) == len(chunks))
    check("every chunk points to a registered source", all(c["source_id"] in ids for c in chunks))
    bad_hash = [c["chunk_id"] for c in chunks if hashlib.sha256(c["text"].encode("utf-8")).hexdigest() != c["text_sha256"]]
    check("chunk text hashes recompute", not bad_hash, f"{len(bad_hash)} mismatched" if bad_hash else "")
    mism = []
    for f, m in manifest.items():
        p = ROOT / "kb" / "raw" / f
        if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() != m["sha256"]:
            mism.append(f)
    check("raw files match the download manifest", not mism, ", ".join(mism))
    long_pub = [c["chunk_id"] for c in public if c["redistribute"] == "excerpt" and len(c["text"].split()) > 61]
    check("public export is excerpt-only for excerpt sources (<= 60 words + marker)", not long_pub, f"{len(long_pub)} too long" if long_pub else "")
    check("no source is marked 'full' redistribution without a licence review", all(s["redistribute"] != "full" for s in reg), "all sources are excerpt-only")
    check("every ingested source has a canonical URL", all(s["url"].startswith("http") for s in reg if status[s["id"]]))
    check("all chunks marked not-legally-reviewed", all(c["review_status"] == "not-legally-reviewed" for c in chunks))
    check("clinical-content sources labelled clinical-unreviewed",
          all(c["clinical_review"] == "clinical-unreviewed" for c in chunks if next(s for s in reg if s["id"] == c["source_id"])["clinical_content"]))

    ing = [r for r in rows if r["ingested"]]
    pend = [r for r in rows if not r["ingested"]]
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    md = [
        "# KB v1 coverage check",
        "",
        f"Generated {when} by `kb/coverage.py`. Source of truth: `sources/sources.json`. Build: `{report['build_id']}`.",
        "",
        f"**Headline:** {len(ing)} of {len(rows)} listed sources are in the KB ({sum(r['chunks'] for r in rows)} chunks, {sum(r['words'] for r in rows):,} words). "
        f"{len(pend)} are listed but NOT ingested (they need a person to download a file, see below). "
        f"{sum(1 for r in ing if r['partial'])} ingested sources are partial. Nothing here has been checked by a lawyer or a clinician.",
        "",
        "## 1. Coverage of the plan's required document families",
        "",
        "| Required by the plan | Sources | In KB | Verdict |",
        "|---|---|---|---|",
    ]
    for name, sids in REQUIRED:
        have = [x for x in sids if status.get(x)]
        verdict = "covered" if len(have) == len(sids) else ("partly covered" if have else "NOT covered")
        if verdict == "covered" and any(r["partial"] for r in rows if r["id"] in sids):
            verdict = "covered, but at least one source is partial"
        md.append(f"| {name} | {', '.join(sids)} | {len(have)} of {len(sids)} | {verdict} |")
    md += [
        "",
        "## 2. Per-source status",
        "",
        "| Source | Kind | Level | In KB | Chunks | Words | PDF pages covered | No-text pages | Fetch | Currency note |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        pg = "-" if r["pages_covered"] is None else (f"{r['pages_covered']}" + (f" of {r['pages_expected']}" if r["pages_expected"] else ""))
        md.append(f"| {r['id']} | {r['kind']} | {r['jurisdiction']} | {'yes' + (' (partial)' if r['partial'] else '') if r['ingested'] else 'NO'} | {r['chunks']} | {r['words']} | {pg} | {len(r['empty_pages']) or '-'} | {r['method']} | {r['version_status']} |")
    md += [
        "",
        "## 3. Listed but not ingested (what Sumit or a teammate has to do)",
        "",
    ]
    for s in reg:
        if not status[s["id"]]:
            md.append(f"- **{s['id']}**: {s['fetch'].get('reason', '')}")
    md += [
        "",
        "## 4. Integrity checks (automatic)",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for c in checks:
        md.append(f"| {c['check']} | {'PASS' if c['ok'] else 'FAIL'} | {c['detail']} |")
    md += [
        "",
        "## 5. Known limitations of KB v1",
        "",
        "- **Not legally reviewed.** No UAE lawyer has checked any chunk or any mapping. Clinical material is labelled `clinical-unreviewed`; no clinician (including Dr. Neeta) has signed off on anything here.",
        "- **Translations.** English versions only. Where the portal says the Arabic text prevails, the Arabic text is the binding one.",
        "- **Partial PDPL.** Only articles 1, 2, 4, 5, 6, 9, 13, 17, 18, 20-23 are in the KB. The Executive Regulations are not in the KB and their status is not confirmed here.",
        "- **Decision 51/2021 is the ministry's summary, not the resolution.** The binding Arabic text is a MOHAP PDF.",
        "- **Federal Law 2/2019 and its Executive Regulations come from the Abu Dhabi DoH compilation (Book 10).** The compilation is 'all rights reserved'; replace it with the legislation-portal text and keep the same chunk ids.",
        "- **Possible staleness.** Several policies show a revision date that has already passed (DHA AI policy: 2026-07-01; DHA Telehealth Policy: 2026-08-16) or are old drafts (DoH AI policy v0.9, 2018; NMC advertising guide predates the current media law). The KB records the version note per chunk; it does not know whether a newer version exists.",
        "- **Scanned pages.** Pages with no text layer are not in the KB (counts in section 2).",
        "- **Retrieval is lexical (BM25).** It can miss answers that need a second hop, for example the penalty clause (Art. 24) for the localisation rule (Art. 13). See RETRIEVAL_TESTS.md.",
        "- **Pipeline mapping (nodes, dimensions) is the analyst's own and unreviewed.**",
        "",
    ]
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "KB_COVERAGE.md").write_text("\n".join(md), encoding="utf-8")
    (ROOT / "kb" / "out" / "coverage.json").write_text(json.dumps({"generated": when, "rows": rows, "checks": checks}, indent=2), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"sources in KB: {len(ing)}/{len(rows)}; chunks {len(chunks)}")
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["check"], c["detail"])
    return 0 if all(c["ok"] for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
