"""Unit and integration tests for the KB pipeline.  Run:  python -m unittest discover -s kb/tests -v"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "kb"))

import build_kb  # noqa: E402
import search  # noqa: E402

CHUNKS = ROOT / "kb" / "out" / "chunks.jsonl"
PUBLIC = ROOT / "kb" / "out" / "public" / "chunks_public.jsonl"


def load(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


class Headings(unittest.TestCase):
    def test_long_article_title_is_detected(self):
        h = build_kb.heading_of("Article (22) Cross-Border Transfer and Sharing of Personal Data for Processing Purposes if a Proper Protection Level is Available")
        self.assertEqual(h[0], "article")
        self.assertTrue(h[1].startswith("Art. 22"))

    def test_plain_article_and_non_heading(self):
        self.assertEqual(build_kb.heading_of("Article (13)")[1], "Art. 13")
        self.assertIsNone(build_kb.heading_of("The Controller shall take appropriate measures."))

    def test_numbered_heading_not_used_for_laws(self):
        self.assertIsNone(build_kb.heading_of("4. Other conditions of joining", allow_numbered=False))
        self.assertIsNotNone(build_kb.heading_of("4. Policy Statement", allow_numbered=True))


class Chunking(unittest.TestCase):
    def test_law_breaks_at_every_article_and_tracks_pages(self):
        src = {"kind": "law"}
        pages = [(1, "Article (1) First\nalpha beta gamma\nArticle (2) Second\ndelta epsilon"), (2, "zeta eta theta")]
        ch = build_kb.chunk_source(src, pages)
        self.assertEqual([c["section"] for c in ch], ["Art. 1 First", "Art. 2 Second"])
        self.assertEqual((ch[1]["page_start"], ch[1]["page_end"]), (1, 2))

    def test_long_text_uses_overlap(self):
        words = " ".join(f"w{i}" for i in range(600))
        ch = build_kb.chunk_source({"kind": "policy"}, [(1, words)])
        self.assertGreaterEqual(len(ch), 3)
        first, second = ch[0]["text"].split(), ch[1]["text"].split()
        self.assertEqual(first[-build_kb.OVERLAP_WORDS:], second[:build_kb.OVERLAP_WORDS])


class Retrieval(unittest.TestCase):
    def test_spelling_and_synonyms(self):
        self.assertEqual(search.normalise("Anonymization authorization"), "anonymisation authorisation")
        w = search.weighted_query("What is the fine abroad?")
        self.assertEqual(w["fine"], 1.0)
        self.assertEqual(w["penalty"], 0.6)

    def test_evidence_gate(self):
        self.assertEqual(search.evidence_level([]), "none")
        self.assertEqual(search.evidence_level([{"score": 20, "coverage": 0.8}]), "strong")
        self.assertEqual(search.evidence_level([{"score": 20, "coverage": 0.5}]), "weak")
        self.assertEqual(search.evidence_level([{"score": 12, "coverage": 1.0}]), "weak")
        self.assertEqual(search.evidence_level([{"score": 6, "coverage": 1.0}]), "none")


@unittest.skipUnless(CHUNKS.exists(), "run kb/build_kb.py first")
class BuiltKB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load(CHUNKS)
        cls.pub = load(PUBLIC)

    def test_pdpl_cross_border_articles_have_correct_locators(self):
        loc = {r["locator"].split(",")[0][:7] for r in self.rows if r["source_id"] == "UAE-PDPL-2021"}
        self.assertTrue({"Art. 22", "Art. 23"} <= loc)
        art23 = [r for r in self.rows if r["source_id"] == "UAE-PDPL-2021" and r["locator"].startswith("Art. 23")]
        self.assertTrue(any("explicit consent" in r["text"] for r in art23))

    def test_fl2_article_13_and_24(self):
        a13 = [r for r in self.rows if r["source_id"] == "UAE-FL2-2019" and r["locator"].startswith("Art. 13")]
        self.assertTrue(a13 and a13[0]["text"].startswith("Article (13)"))
        a24 = [r for r in self.rows if r["source_id"] == "UAE-FL2-2019" and r["locator"].startswith("Art. 24")]
        self.assertTrue(a24 and "500,000" in a24[0]["text"])

    def test_article_locator_matches_heading_inside_text_for_laws(self):
        bad = []
        for r in self.rows:
            if r["kind"] in {"law", "regulation"}:
                m = re.match(r"Article\s*\(?(\d+)\)?", r["text"])
                if m and not r["locator"].startswith(f"Art. {m.group(1)}"):
                    bad.append((r["chunk_id"], r["locator"], m.group(1)))
        self.assertEqual(bad, [])

    def test_every_chunk_has_citation_and_url(self):
        for r in self.rows:
            self.assertTrue(r["citation"].startswith(f"[{r['source_id']}]"))
            self.assertTrue(r["url"].startswith("http"))
            self.assertEqual(len(r["text_sha256"]), 64)

    def test_public_export_is_excerpt_only(self):
        for r in self.pub:
            if r["redistribute"] == "excerpt":
                self.assertLessEqual(len(r["text"].split()), 61, r["chunk_id"])

    def test_known_gap_sources_are_absent(self):
        present = {r["source_id"] for r in self.rows}
        for sid in ("UAE-FDL38-2024", "UAE-FL15-2020", "UAE-FDL4-2016", "WHO-AI-HEALTH-2021"):
            self.assertNotIn(sid, present)


if __name__ == "__main__":
    unittest.main()
