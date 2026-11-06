"""Retrieval over the Miqyas KB: BM25 (pure Python, no model, no network) with citations.

Why BM25 first: it is deterministic, free, and runs offline, so every retrieval result is
reproducible and auditable. The chunk records are also exported in the ITU reference
schema (kb/export_itu_chroma.py) so a vector index can be added on top without changing
the citations.

Every result carries: citation id, section/article, PDF page range, URL, document date,
version status, licence handling and review status. The result also says how strong the
evidence is ("strong" / "weak" / "none") so an agent can abstain instead of guessing.

CLI:  python kb/search.py "may health data be stored outside the UAE" -k 5
      python kb/search.py "..." --public          (search the shareable excerpt export)
      python kb/search.py "..." --source UAE-FL2-2019 --mandate DHA --json
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FULL = ROOT / "kb" / "out" / "chunks.jsonl"
PUBLIC = ROOT / "kb" / "out" / "public" / "chunks_public.jsonl"

STOP = set(
    "a an and are as at be but by can could do does for from has have how if in into is it its may "
    "must of on or our shall should that the their there these they this to under was were what when "
    "where which who whom whose why will with would you your i we not no any all also than then so such "
    "uae".split()
)
SUFFIXES = ("ations", "ation", "ings", "ing", "ied", "ies", "ed", "es", "s")


# Query-time expansion: domain synonyms fixed a priori (legal / health / advertising wording),
# not derived from the test cases. Expansion terms count 0.6 of an original term.
SYNONYMS = {
    "fine": ["penalty", "punish"], "penalty": ["fine", "punish"], "sanction": ["penalty", "fine"],
    "abroad": ["outside"], "overseas": ["outside"], "offshore": ["outside"],
    "influencer": ["endorse", "promotion"], "sponsor": ["endorse", "promotion"],
    "wearable": ["device", "equipment"], "smartwatch": ["device", "equipment", "radio"],
    "approval": ["authorisation", "approve"], "permission": ["authorisation", "approve"],
    "doctor": ["physician", "practitioner", "professional"], "clinician": ["practitioner", "professional"],
    "clinic": ["facility", "establishment"], "hospital": ["facility", "establishment"],
    "ad": ["advertisement", "advertising"], "ads": ["advertisement", "advertising"], "advert": ["advertisement", "advertising"],
    "share": ["disclose", "exchange"], "sharing": ["disclose", "exchange"],
    "explain": ["explainability", "transparency"], "explained": ["explainability", "transparency"],
    "wrong": ["error", "harm"], "harmful": ["harm", "risk"],
}


def normalise(text: str) -> str:
    """British/American spelling variants (authorization/authorisation, anonymization/anonymisation)."""
    t = text.lower()
    t = re.sub(r"(\w)iz(ation|ations|e|ed|es|ing)\b", r"\1is\2", t)
    return t


def stem(w: str) -> str:
    for suf in SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)] + ("y" if suf in {"ies", "ied"} else "")
    return w


def tokens(text: str) -> list[str]:
    return [stem(t) for t in re.findall(r"[^\W_]+", normalise(text)) if t not in STOP and len(t) > 1]


def weighted_query(query: str, expand: bool = True) -> dict[str, float]:
    """Stemmed query terms with weights: 1.0 for the user's words, 0.6 for synonym expansions."""
    w: dict[str, float] = {}
    for raw in re.findall(r"[^\W_]+", normalise(query)):
        if raw in STOP or len(raw) < 2:
            continue
        w[stem(raw)] = 1.0
    if expand:
        for raw in re.findall(r"[^\W_]+", normalise(query)):
            for syn in SYNONYMS.get(raw, []):
                w.setdefault(stem(syn), 0.6)
    return w


class KB:
    def __init__(self, path: Path = FULL):
        self.chunks = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.tf: list[Counter] = []
        self.len: list[int] = []
        df: Counter = Counter()
        for c in self.chunks:
            # section and title are indexed too, so "Article 13" or "telehealth" queries find the right place
            toks = tokens(c["text"]) + tokens(c["section"]) * 2 + tokens(c["title"])
            tf = Counter(toks)
            self.tf.append(tf)
            self.len.append(sum(tf.values()))
            df.update(tf.keys())
        self.N = len(self.chunks)
        self.avg = sum(self.len) / max(1, self.N)
        self.idf = {t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in df.items()}

    def search(self, query: str, k: int = 5, source=None, mandate=None, kind=None, jurisdiction=None,
               node=None, k1: float = 1.5, b: float = 0.75, expand: bool = True):
        qw = weighted_query(query, expand)
        qset = list(qw)
        scored = []
        for i, c in enumerate(self.chunks):
            if source and c["source_id"] not in source:
                continue
            if mandate and not (set(mandate) & set(c["mandates"])):
                continue
            if kind and c["kind"] not in kind:
                continue
            if jurisdiction and c["jurisdiction"] not in jurisdiction:
                continue
            if node and not (set(node) & set(c["nodes"])):
                continue
            tf, dl = self.tf[i], self.len[i]
            s = 0.0
            for t in qset:
                f = tf.get(t, 0)
                if f:
                    s += qw[t] * self.idf.get(t, 0) * f * (k1 + 1) / (f + k1 * (1 - b + b * dl / self.avg))
            if s > 0:
                scored.append((s, i))
        scored.sort(reverse=True)
        total_idf = sum(qw[t] * self.idf.get(t, 0) for t in qset) or 1.0
        out = []
        for s, i in scored[:k]:
            c = self.chunks[i]
            matched = sum(qw[t] * self.idf.get(t, 0) for t in qset if self.tf[i].get(t, 0))
            cov = matched / total_idf
            out.append({"score": round(s, 3), "coverage": round(cov, 3), **c})
        return out


STRONG_SCORE, STRONG_COVERAGE, WEAK_SCORE = 15.0, 0.70, 10.0


def evidence_level(results) -> str:
    """Evidence gate (rule v2). An agent may answer from the KB alone only when evidence is 'strong'.

    strong: top BM25 score >= 15 and >= 70% of the query's information-bearing terms (IDF weighted) in the top chunk
    weak  : top score >= 10 (partial evidence: answer with a caveat or ask a human)
    none  : top score < 10 (abstain)
    Scores depend on this corpus's IDF statistics; re-check the thresholds when the corpus changes.
    """
    if not results:
        return "none"
    top = results[0]
    if top["score"] >= STRONG_SCORE and top["coverage"] >= STRONG_COVERAGE:
        return "strong"
    return "weak" if top["score"] >= WEAK_SCORE else "none"


def fmt(r, width: int = 360) -> str:
    snippet = re.sub(r"\s+", " ", r["text"])[:width]
    return (
        f"{r['citation']}  score={r['score']} cov={r['coverage']}\n"
        f"    {r['title']} | {r['issuer']} | {r['doc_date']} | {r['version_status']}\n"
        f"    {r['url']}\n"
        f"    review: {r['review_status']} / {r['clinical_review']} | licence handling: {r['redistribute']}\n"
        f"    \"{snippet}…\""
    )


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--public", action="store_true")
    ap.add_argument("--source", action="append")
    ap.add_argument("--mandate", action="append")
    ap.add_argument("--kind", action="append")
    ap.add_argument("--jurisdiction", action="append")
    ap.add_argument("--node", action="append")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.k < 1:
        ap.error("-k must be 1 or more")
    use_public = a.public or not FULL.exists()
    if use_public and not a.public:
        print("full text not built here: searching the public excerpts instead", file=sys.stderr)
    kb = KB(PUBLIC if use_public else FULL)
    res = kb.search(a.query, a.k, a.source, a.mandate, a.kind, a.jurisdiction, a.node)
    if a.json:
        print(json.dumps({"evidence": evidence_level(res), "results": res}, ensure_ascii=False, indent=2))
    else:
        print(f"evidence: {evidence_level(res)}  ({len(res)} results)\n")
        for r in res:
            print(fmt(r), "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
