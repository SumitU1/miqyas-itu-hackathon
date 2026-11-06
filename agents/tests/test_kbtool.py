import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "kb"))

from agents.audit import AuditLog  # noqa: E402
from agents.kbtool import KBTool, load_kb  # noqa: E402
from agents.roles import ROLES  # noqa: E402

KB = load_kb()


class KBToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "run.jsonl"
        self.audit = AuditLog(self.path, "t")
        self.tool = KBTool(KB, self.audit)

    def tearDown(self):
        self.tmp.cleanup()

    def records(self):
        return [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines()]

    def test_every_query_is_logged_with_chunk_ids_scores_and_evidence(self):
        r = self.tool.query("agent:adviser", "may health data be stored outside the UAE")
        rec = self.records()[-1]
        self.assertEqual(rec["type"], "kb_query")
        self.assertEqual(rec["payload"]["chunk_ids"], [c["chunk_id"] for c in r["results"]])
        self.assertEqual(rec["payload"]["evidence"], r["evidence"])
        self.assertEqual(rec["payload"]["kb_build_id"], KB.chunks[0]["build_id"])

    def test_scope_limits_results_to_the_listed_sources(self):
        scope = ROLES["clinic"].scope
        r = self.tool.query("agent:clinic", "personal data cross-border transfer consent", scope=scope, k=10)
        self.assertTrue(r["results"])
        self.assertTrue({c["source_id"] for c in r["results"]} <= set(scope))
        self.assertEqual(self.records()[-1]["payload"]["filters"]["scope"], sorted(scope))

    def test_scopes_are_disjoint_where_the_brief_needs_information_asymmetry(self):
        coach, clinic, auth = (set(ROLES[r].scope) for r in ("coach", "clinic", "authority"))
        self.assertFalse(coach & clinic)
        self.assertFalse(coach & auth)
        self.assertFalse(clinic & auth)

    def test_every_scope_entry_is_a_registered_source(self):
        reg = json.loads((ROOT / "sources" / "sources.json").read_text(encoding="utf-8"))
        ids = {s["id"] for s in (reg if isinstance(reg, list) else reg["sources"])}
        for role in ROLES.values():
            if role.scope is not None:
                self.assertTrue(set(role.scope) <= ids, role.name)
        self.assertIsNone(ROLES["adviser"].scope, "the Adviser reads the whole KB")

    def test_off_topic_query_has_no_strong_evidence_and_is_still_logged(self):
        r = self.tool.query("agent:adviser", "best recipe for lamb biryani")
        self.assertNotEqual(r["evidence"], "strong")
        self.assertEqual(self.records()[-1]["payload"]["evidence"], r["evidence"])

    def test_get_returns_the_chunk_and_none_for_an_invented_id(self):
        cid = KB.chunks[5]["chunk_id"]
        self.assertEqual(self.tool.get(cid)["chunk_id"], cid)
        self.assertIsNone(self.tool.get("UAE-FL2-2019:9999"))

    def test_rank_of_finds_the_cited_chunk_for_its_own_wording(self):
        c = next(c for c in KB.chunks if c["source_id"] == "UAE-FL2-2019" and "outside the State" in c["text"])
        rank = self.tool.rank_of("health data stored or processed outside the State", c["chunk_id"], top=30)
        self.assertIsNotNone(rank)


if __name__ == "__main__":
    unittest.main()
