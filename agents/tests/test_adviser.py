import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from agents.adviser import Adviser, chunk_caveats, detect_conflicts  # noqa: E402
from agents.audit import AuditLog  # noqa: E402
from agents.kbtool import KBTool, load_kb  # noqa: E402
from agents.testing import ScriptedModel  # noqa: E402

FULL_KB = ROOT / "kb" / "out" / "chunks.jsonl"
KB = load_kb()
STRONG_Q = "what must a telehealth provider do before sharing patient information with another facility"
WEAK_Q = "may health data be stored outside the UAE"
NONE_Q = "best recipe for lamb biryani"


def first(source):
    return next(c for c in KB.chunks if c["source_id"] == source)


class Caveats(unittest.TestCase):
    def test_caveats_come_from_the_chunk_record_not_from_the_model(self):
        self.assertIn("revision-date-passed", chunk_caveats(first("DHA-AI-2021")))
        self.assertIn("summary-only", chunk_caveats(first("MOHAP-MD51-2021")))
        self.assertIn("partial-capture", chunk_caveats(first("UAE-PDPL-2021")))
        self.assertIn("non-binding", chunk_caveats(first("DUBAI-AI-ETHICS-2022")))
        self.assertIn("may-be-superseded", chunk_caveats(first("NMC-AD-GUIDE")))
        self.assertIn("currency-unconfirmed", chunk_caveats(first("DOH-AI-2018")))
        self.assertIn("clinical-unreviewed", chunk_caveats(next(c for c in KB.chunks if c["clinical_review"] == "clinical-unreviewed")))


class Conflicts(unittest.TestCase):
    def a(self, agent, cls, provisions=(), status="ok"):
        return {"agent": agent, "status": status, "proposed_action": {"class": cls}, "provisions": list(provisions)}

    def test_share_against_withhold_is_a_conflict(self):
        flags = detect_conflicts([self.a("clinic", "share"), self.a("authority", "withhold")], KB.by_id if hasattr(KB, "by_id") else {c["chunk_id"]: c for c in KB.chunks})
        self.assertIn("action-conflict", [f["type"] for f in flags])

    def test_agreeing_actions_are_not_a_conflict(self):
        flags = detect_conflicts([self.a("clinic", "withhold"), self.a("authority", "withhold")], {})
        self.assertEqual(flags, [])

    def test_citations_spread_over_jurisdictions_are_flagged(self):
        by_id = {c["chunk_id"]: c for c in KB.chunks}
        dub = next(c["chunk_id"] for c in KB.chunks if c["jurisdiction"] == "dubai")
        ad = next(c["chunk_id"] for c in KB.chunks if c["jurisdiction"] == "abu-dhabi")
        flags = detect_conflicts([self.a("clinic", "share", [dub]), self.a("authority", "share", [ad])], by_id)
        spread = [f for f in flags if f["type"] == "jurisdiction-spread"]
        self.assertTrue(spread)
        self.assertEqual(set(spread[0]["jurisdictions"]), {"dubai", "abu-dhabi"})

    def test_federal_law_plus_one_emirate_is_normal_layering_and_not_flagged(self):
        by_id = {c["chunk_id"]: c for c in KB.chunks}
        fed = next(c["chunk_id"] for c in KB.chunks if c["jurisdiction"] == "federal")
        dub = next(c["chunk_id"] for c in KB.chunks if c["jurisdiction"] == "dubai")
        flags = detect_conflicts([self.a("clinic", "share", [fed]), self.a("authority", "share", [dub])], by_id)
        self.assertNotIn("jurisdiction-spread", [f["type"] for f in flags])

    def test_a_missing_assessment_is_flagged(self):
        flags = detect_conflicts([self.a("clinic", "escalate_to_human", status="model_unavailable")], {})
        self.assertIn("missing-assessment", [f["type"] for f in flags])


@unittest.skipUnless(FULL_KB.exists(), "needs the full-text KB (kb/out/chunks.jsonl), rebuilt with scripts/fetch_sources.py then kb/build_kb.py")
class AdviserTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "run.jsonl"
        self.audit = AuditLog(self.path, "t")
        self.tool = KBTool(KB, self.audit)

    def tearDown(self):
        self.tmp.cleanup()

    def adviser(self, script):
        self.model = ScriptedModel(script)
        return Adviser(self.tool, self.model, self.audit)

    def top_ids(self, q, n=2):
        return [c["chunk_id"] for c in self.tool.query("probe", q, k=n)["results"]]

    def test_strong_evidence_gives_a_ruling_with_valid_citations(self):
        ids = self.top_ids(STRONG_Q)
        adv = self.adviser([{"ruling": "The text says the sender must ...", "provisions": ids[:1], "conditions": []}])
        out = adv.answer(STRONG_Q, asked_by="agent:clinic")
        self.assertEqual(out["evidence"], "strong")
        self.assertEqual(out["outcome"], "ruling")
        self.assertEqual(out["provisions"], ids[:1])
        self.assertEqual(self.model.calls, 1)

    def test_a_model_that_returns_strings_where_lists_are_expected_is_handled(self):
        ids = self.top_ids(STRONG_Q)
        adv = self.adviser([{"ruling": "The text says ...", "provisions": ids[0], "conditions": "Check consent first"}])
        out = adv.answer(STRONG_Q, asked_by="agent:clinic")
        self.assertEqual(out["outcome"], "ruling")
        self.assertEqual(out["provisions"], [ids[0]])
        self.assertEqual(out["conditions"], ["Check consent first"])

    def test_weak_evidence_abstains_without_calling_the_model_and_lists_passages_for_a_human(self):
        adv = self.adviser([])
        out = adv.answer(WEAK_Q, asked_by="agent:authority")
        self.assertEqual(out["evidence"], "weak")
        self.assertEqual(out["outcome"], "abstain")
        self.assertEqual(self.model.calls, 0)
        self.assertTrue(out["for_human"])
        self.assertIsNone(out["ruling"])

    def test_no_evidence_abstains(self):
        out = self.adviser([]).answer(NONE_Q, asked_by="agent:coach")
        self.assertEqual(out["outcome"], "abstain")
        self.assertIn(out["evidence"], ("none", "weak"))
        self.assertNotEqual(out["evidence"], "strong")

    def test_a_ruling_that_cites_an_unretrieved_chunk_is_discarded(self):
        adv = self.adviser([{"ruling": "x", "provisions": ["UAE-FL2-2019:9999"], "conditions": []}])
        out = adv.answer(STRONG_Q, asked_by="agent:clinic")
        self.assertEqual(out["outcome"], "abstain")
        self.assertEqual(out["abstain_reason"], "citation-check-failed")
        self.assertIsNone(out["ruling"])

    def test_a_null_or_blank_ruling_is_not_accepted_as_a_ruling(self):
        ids = self.top_ids(STRONG_Q)
        for bad in (None, "  ", 5, ["x"]):
            adv = self.adviser([{"ruling": bad, "provisions": ids[:1], "conditions": []}] * 2)
            out = adv.answer(STRONG_Q, asked_by="agent:clinic")
            self.assertEqual(out["outcome"], "abstain", bad)
            self.assertEqual(out["abstain_reason"], "unparseable-reply", bad)
            self.assertIsNone(out["ruling"], bad)
            self.assertEqual(self.model.calls, 2, bad)

    def test_a_null_ruling_then_a_good_one_is_used(self):
        ids = self.top_ids(STRONG_Q)
        adv = self.adviser([{"ruling": None, "provisions": ids[:1]}, {"ruling": "The text says ...", "provisions": ids[:1]}])
        out = adv.answer(STRONG_Q, asked_by="agent:clinic")
        self.assertEqual(out["outcome"], "ruling")
        self.assertTrue(out["ruling"].startswith("The text says ..."))

    def test_the_rejected_ids_are_recorded_and_the_model_gets_one_more_try_with_the_allowed_ids(self):
        bad = {"ruling": "x", "provisions": ["UAE-FL2-2019:9999"], "conditions": []}
        adv = self.adviser([bad, bad])
        out = adv.answer(STRONG_Q, asked_by="x")
        self.assertEqual(out["rejected_citations"], ["UAE-FL2-2019:9999"])
        self.assertEqual(self.model.calls, 2)
        self.assertIn(out["retrieved"][0], self.model.prompts[1]["user"].split("Cite only")[-1])

    def test_a_second_attempt_with_valid_ids_becomes_a_ruling(self):
        ids = self.top_ids(STRONG_Q)
        adv = self.adviser([{"ruling": "x", "provisions": ["NOPE:1"], "conditions": []},
                            {"ruling": "The text says ...", "provisions": ids[:1], "conditions": []}])
        out = adv.answer(STRONG_Q, asked_by="x")
        self.assertEqual(out["outcome"], "ruling")
        self.assertEqual(out["provisions"], ids[:1])

    def test_a_ruling_with_no_citation_is_discarded(self):
        adv = self.adviser([{"ruling": "trust me", "provisions": [], "conditions": []}] * 2)
        self.assertEqual(adv.answer(STRONG_Q, asked_by="x")["abstain_reason"], "citation-check-failed")

    def test_planning_tries_short_keyword_queries_and_keeps_the_best_evidence(self):
        ids = self.top_ids(STRONG_Q)
        adv = self.adviser([{"queries": [STRONG_Q, "recipe biryani"]},
                            {"ruling": "The text says ...", "provisions": ids[:1], "conditions": []}])
        adv.plan_queries = True
        out = adv.answer("Our clinic wants to pass a patient's file to another clinic, what is needed?", asked_by="x")
        self.assertEqual(out["evidence"], "strong")
        self.assertEqual(out["query_used"], STRONG_Q)
        self.assertEqual(len(out["queries_tried"]), 3)               # the raw question + 2 planned
        logged = [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len([r for r in logged if r["type"] == "kb_query" and r["actor"] == "agent:adviser"]), 3)

    def test_planning_cannot_lower_the_evidence_and_failure_falls_back_to_the_raw_question(self):
        adv = self.adviser([None, None])
        adv.plan_queries = True
        out = adv.answer(WEAK_Q, asked_by="x")
        self.assertEqual(out["query_used"], WEAK_Q)
        self.assertEqual(out["evidence"], "weak")
        self.assertEqual(out["outcome"], "abstain")

    def test_planning_is_off_by_default(self):
        adv = self.adviser([])
        out = adv.answer(WEAK_Q, asked_by="x")
        self.assertEqual(self.model.calls, 0)
        self.assertEqual(len(out["queries_tried"]), 1)

    def test_model_failure_abstains(self):
        out = self.adviser([None, None]).answer(STRONG_Q, asked_by="x")
        self.assertEqual(out["outcome"], "abstain")
        self.assertEqual(out["abstain_reason"], "model-unavailable")

    def test_guidance_documents_are_never_presented_as_binding(self):
        ids = [c["chunk_id"] for c in KB.chunks if c["source_id"] == "DUBAI-AI-ETHICS-2022"][:1]
        adv = self.adviser([])
        adv.model = ScriptedModel([{"ruling": "r", "provisions": ids, "conditions": []}])
        out = adv._finish(ids, "r", [], retrieved=ids, evidence="strong", question="q", asked_by="x")
        self.assertFalse(out["binding"])
        self.assertIn("not binding law", out["ruling"].lower())

    def test_the_prompt_forbids_legal_advice_and_summary_as_binding(self):
        ids = self.top_ids(STRONG_Q)
        adv = self.adviser([{"ruling": "r", "provisions": ids[:1], "conditions": []}])
        adv.answer(STRONG_Q, asked_by="x")
        s = self.model.prompts[0]["system"].lower()
        self.assertIn("not legal advice", s)
        self.assertIn("summary", s)

    def test_verify_marks_each_citation_with_page_url_caveats_and_support(self):
        cid = self.top_ids(STRONG_Q, 1)[0]
        adv = self.adviser([])
        v = adv.verify([{"agent": "clinic", "finding": STRONG_Q, "provisions": [cid], "citation_violations": ["X:1"]}])
        row = v[0]
        self.assertEqual(row["agent"], "clinic")
        self.assertEqual(row["citation_violations"], ["X:1"])
        c = row["citations"][0]
        self.assertEqual(c["chunk_id"], cid)
        self.assertTrue(c["exists"])
        self.assertIn(c["support"], ("supported", "loosely-supported"))
        self.assertTrue(c["url"].startswith("http"))
        self.assertIn("p", c["locator"])
        self.assertIsInstance(c["caveats"], list)

    def test_verify_marks_a_real_chunk_that_does_not_fit_the_finding(self):
        unrelated = next(c["chunk_id"] for c in KB.chunks if c["source_id"] == "TDRA-IOT-PROC-V1")
        v = self.adviser([]).verify([{"agent": "clinic", "finding": "telehealth consent for sharing records between facilities", "provisions": [unrelated], "citation_violations": []}])
        self.assertEqual(v[0]["citations"][0]["support"], "not-supported-by-finding-text")

    def test_the_ruling_prompt_says_decision_ids_are_not_chunk_ids(self):
        from agents.adviser import SYSTEM
        self.assertIn("decision ids", SYSTEM)
        self.assertIn("not chunk ids", SYSTEM)


if __name__ == "__main__":
    unittest.main()
