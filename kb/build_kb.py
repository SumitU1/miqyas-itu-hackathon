"""Build the Miqyas UAE health-policy knowledge base (KB v1).

Same shape as the ITU reference ingestion (ITUAIReadiness: parse -> chunk by words ->
metadata per chunk), but every chunk also carries a citation: source id, section or
article, PDF page range, canonical URL, document date and a hash of the raw file and of
the chunk text, so any answer can be traced back to a public document.

Reads  : sources/sources.json, kb/raw/*
Writes : kb/out/chunks.jsonl            full text   (local only, git-ignored)
         kb/out/public/chunks_public.jsonl  shareable export (excerpts per licence)
         kb/out/build_report.json       counts and warnings

Usage  : python kb/build_kb.py
Needs  : Python 3.10+, PyMuPDF (pip install pymupdf) for PDF parsing.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "kb" / "raw"
OUT = ROOT / "kb" / "out"

CHUNK_WORDS = 256   # same as ITU reference config.py chunk_size
OVERLAP_WORDS = 30  # same as ITU reference config.py chunk_overlap
MIN_TAIL_WORDS = 20
EXCERPT_WORDS = 60  # words kept per chunk in the public export for redistribute=excerpt

ARTICLE_RE = re.compile(r"^\s*Article\s*\(?\s*(\d+)\s*\)?\s*(.{0,260})$", re.I)
NUMBERED_RE = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2}){0,3})\.?\s+([A-Z][^\n]{3,100})$")
CAPS_RE = re.compile(r"^[A-Z][A-Z0-9 ,&/()\-]{7,80}$")
NOISE_RE = re.compile(r"^\s*(Page\s+\d+\s+of\s+\d+|\d{1,3}|Page\s+\d+)\s*$", re.I)
NOTE_RE = re.compile(r"^\[(Captured|Official MOHAP)")


class _Text(HTMLParser):
    SKIP = {"script", "style", "nav", "header", "footer", "noscript", "svg"}

    def __init__(self):
        super().__init__()
        self.depth_skip = 0
        self.out: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.depth_skip += 1
        if tag in {"p", "div", "li", "br", "h1", "h2", "h3", "h4", "tr"}:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.depth_skip:
            self.depth_skip -= 1

    def handle_data(self, data):
        if not self.depth_skip:
            self.out.append(data)


def parse_pdf(path: Path, pages: list[int] | None):
    """Return (list of (page_no, text)), list of empty page numbers."""
    import fitz  # PyMuPDF

    doc = fitz.open(str(path))
    lo, hi = (pages or [1, len(doc)])
    out, empty = [], []
    for i in range(lo - 1, min(hi, len(doc))):
        t = doc[i].get_text()
        if len(t.strip()) < 25:
            empty.append(i + 1)
        out.append((i + 1, t))
    # drop running headers/footers: short lines that repeat on many pages
    if len(out) >= 6:
        from collections import Counter

        freq = Counter()
        for _, t in out:
            for ln in {x.strip() for x in t.splitlines() if x.strip()}:
                freq[ln] += 1
        limit = max(3, int(0.3 * len(out)))
        noisy = {ln for ln, c in freq.items() if c >= limit and len(ln) < 90}
        out = [(pn, "\n".join(x for x in t.splitlines() if x.strip() not in noisy)) for pn, t in out]
    return out, empty


def parse_text(path: Path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    note, kept = None, []
    for line in raw.splitlines():
        if note is None and NOTE_RE.match(line.strip()):
            note = line.strip().strip("[]")  # capture note: kept as metadata, not as KB text
        else:
            kept.append(line)
    return [(None, "\n".join(kept))], [], note


def parse_html(path: Path):
    p = _Text()
    p.feed(path.read_text(encoding="utf-8", errors="replace"))
    return [(None, html.unescape("".join(p.out)))], [], None


def heading_of(line: str, allow_numbered: bool = True):
    """Return (kind, label) if the line is a heading, else None."""
    s = line.strip()
    if not s:
        return None
    m = ARTICLE_RE.match(s)
    if m:
        title = re.sub(r"\s+", " ", m.group(2)).strip(" :-")
        label = f"Art. {m.group(1)}" + (f" {title}" if title else "")
        return "article", label[:90]
    if len(s) > 130:
        return None
    m = NUMBERED_RE.match(s)
    if m and allow_numbered and len(m.group(2)) <= 70 and not s.endswith((".", ";", ",")):
        return "numbered", f"§{m.group(1)} {m.group(2).strip()}"[:120]
    if CAPS_RE.match(s) and not NOISE_RE.match(s):
        return "caps", s.title()[:120]
    return None


def chunk_source(src: dict, pages_text: list[tuple]):
    """Yield dicts: text, page_start, page_end, section."""
    force_break_on_article = src["kind"] in {"law", "regulation"}
    words: list[tuple[str, int | None]] = []  # (word, page)
    section = src.get("default_section", "Preamble / front matter")
    chunk_section = section
    chunks: list[dict] = []
    missed: list[str] = []

    def flush(keep_overlap: bool):
        nonlocal words, chunk_section
        if not words:
            return
        pgs = [p for _, p in words if p is not None]
        chunks.append({
            "text": " ".join(w for w, _ in words),
            "page_start": min(pgs) if pgs else None,
            "page_end": max(pgs) if pgs else None,
            "section": chunk_section,
        })
        words = words[-OVERLAP_WORDS:] if keep_overlap else []

    for page, text in pages_text:
        for line in text.splitlines():
            if NOISE_RE.match(line):
                continue
            h = heading_of(line, allow_numbered=not force_break_on_article)
            if force_break_on_article and h is None and re.match(r"^\s*Article\s*\(\d+\)", line):
                missed.append(line.strip()[:60])
            if h:
                kind, label = h
                if kind == "article" and force_break_on_article:
                    flush(keep_overlap=False)
                    words = []
                section = label
                if not words:
                    chunk_section = section
            ws = line.split()
            for w in ws:
                if not words:
                    chunk_section = section
                words.append((w, page))
                if len(words) >= CHUNK_WORDS:
                    flush(keep_overlap=True)
                    chunk_section = section
    flush(keep_overlap=False)

    # merge a tiny tail into the previous chunk (as the ITU reference does)
    if len(chunks) >= 2 and len(chunks[-1]["text"].split()) < MIN_TAIL_WORDS and chunks[-1]["section"] == chunks[-2]["section"]:
        tail = chunks.pop()
        chunks[-1]["text"] += " " + tail["text"]
        if tail["page_end"] is not None:
            chunks[-1]["page_end"] = max(chunks[-1]["page_end"] or 0, tail["page_end"])
    chunk_source.missed = missed
    return chunks


def locator_of(section: str, ps, pe) -> str:
    pg = ""
    if ps is not None:
        pg = f"PDF p.{ps}" if ps == pe else f"PDF pp.{ps}-{pe}"
    return ", ".join(x for x in (section, pg) if x and x != "Preamble / front matter") or "front matter"


def excerpt(text: str, n: int) -> str:
    w = text.split()
    return text if len(w) <= n else " ".join(w[:n]) + " […]"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    reg = json.loads((ROOT / "sources" / "sources.json").read_text(encoding="utf-8"))
    manifest_p = RAW / "MANIFEST.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8")) if manifest_p.exists() else {}
    (OUT / "public").mkdir(parents=True, exist_ok=True)

    build_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")
    all_chunks: list[dict] = []
    report = {"build_id": build_id, "chunk_words": CHUNK_WORDS, "overlap_words": OVERLAP_WORDS, "sources": {}, "warnings": []}

    for src in reg["sources"]:
        f = src["fetch"]["file"]
        path = RAW / f
        rep = {"file": f, "status": None, "chunks": 0, "words": 0, "empty_pages": []}
        report["sources"][src["id"]] = rep
        if not path.exists():
            rep["status"] = "not-ingested: file absent (" + src["fetch"]["method"] + ")"
            continue
        suf = path.suffix.lower()
        note = None
        if suf == ".pdf":
            pages_text, empty = parse_pdf(path, src.get("pages"))
        elif suf in {".txt", ".md"}:
            pages_text, empty, note = parse_text(path)
        elif suf in {".html", ".htm"}:
            pages_text, empty, note = parse_html(path)
        else:
            rep["status"] = f"not-ingested: unsupported type {suf}"
            continue
        rep["empty_pages"] = empty
        if empty:
            report["warnings"].append(f"{src['id']}: {len(empty)} page(s) with no text layer (needs OCR): {empty[:8]}")
        ch = chunk_source(src, pages_text)
        if chunk_source.missed:
            report["warnings"].append(f"{src['id']}: {len(chunk_source.missed)} line(s) look like article headings but were not detected: {chunk_source.missed[:3]}")
        if not ch:
            rep["status"] = "not-ingested: no text extracted"
            continue
        raw_hash = manifest.get(f, {}).get("sha256") or sha(path.read_bytes())
        clin = bool(src.get("clinical_content"))
        for i, c in enumerate(ch, 1):
            loc = locator_of(c["section"], c["page_start"], c["page_end"])
            rec = {
                "chunk_id": f"{src['id']}:{i:04d}",
                "source_id": src["id"],
                "ordinal": i,
                "text": c["text"],
                "n_words": len(c["text"].split()),
                "section": c["section"],
                "page_start": c["page_start"],
                "page_end": c["page_end"],
                "locator": loc,
                "citation": f"[{src['id']}] {loc}",
                "title": src["title"],
                "issuer": src["issuer"],
                "jurisdiction": src["jurisdiction"],
                "kind": src["kind"],
                "ref": src["ref"],
                "doc_date": src["doc_date"],
                "version_status": src["version_status"],
                "url": src["url"],
                "redistribute": src["redistribute"],
                "review_status": "not-legally-reviewed",
                "clinical_review": "clinical-unreviewed" if clin else "not-applicable",
                "nodes": src["nodes"],
                "dimensions": src["dimensions"],
                "topics": src["topics"],
                "mandates": src["mandates"],
                "capture_note": note,
                "source_file_sha256": raw_hash,
                "text_sha256": sha(c["text"].encode("utf-8")),
                "build_id": build_id,
            }
            all_chunks.append(rec)
        rep["status"] = "ingested"
        rep["chunks"] = len(ch)
        rep["words"] = sum(len(c["text"].split()) for c in ch)

    with (OUT / "chunks.jsonl").open("w", encoding="utf-8") as fh:
        for r in all_chunks:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    with (OUT / "public" / "chunks_public.jsonl").open("w", encoding="utf-8") as fh:
        for r in all_chunks:
            p = dict(r)
            if r["redistribute"] == "full":
                pass
            elif r["redistribute"] == "excerpt":
                p["text"] = excerpt(r["text"], EXCERPT_WORDS)
                p["text_is_excerpt"] = True
            else:
                p["text"] = ""
                p["text_is_excerpt"] = True
            fh.write(json.dumps(p, ensure_ascii=False) + "\n")

    report["total_chunks"] = len(all_chunks)
    report["total_words"] = sum(r["n_words"] for r in all_chunks)
    (OUT / "build_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"build {build_id}: {len(all_chunks)} chunks, {report['total_words']} words")
    for sid, r in report["sources"].items():
        print(f"  {sid:<26} {r['status']:<38} chunks={r['chunks']:<4} words={r['words']}")
    for w in report["warnings"]:
        print("WARNING:", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
