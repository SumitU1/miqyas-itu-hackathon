import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from agents.agent import ACTION_CLASSES, RoleAgent  # noqa: E402
from agents.audit import AuditLog  # noqa: E402
from agents.kbtool import KBTool, load_kb  # noqa: E402
from agents.roles import ROLES  # noqa: E402
from agents.testing import ScriptedModel, assessment_json  # noqa: E402

KB = load_kb()
Q = "May the app send the member's health data to a service hosted outside the UAE?"
FACTS = ["The member connected a wearable; heart-rate history is stored on a cloud server whose location is unconfirmed."]


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.audit = AuditLog(Path(self.tmp.name) / "run.jsonl", "t")
        self.tool = KBTool(KB, self.audit)

    def tearDown(self):
        self.tmp.cleanup()

    def agent(self, role, script):
        self.model = ScriptedModel(script)
        return RoleAgent(role, self.tool, self.model, self.audit)

    def retrieved_for(self, role):
        r = self.tool.query("probe", Q, scope=ROLES[role].scope, k=4)
        return [c["chunk_id"] for c in r["results"]]

    def test_the_agent_only_retrieves_from_its_own_mandate(self):
        a = self.agent("clinic", [assessment_json()])
        out = a.assess("S1", 1, Q, FACTS)
        sources = {self.tool.get(i)["source_id"] for i in out["retrieved"]}
        self.assertTrue(sources <= set(ROLES["clinic"].scope), sources)

    def test_valid_citations_are_kept(self):
        cid = self.retrieved_for("authority")[0]
        a = self.agent("authority", [assessment_json(provisions=[cid], cls="withhold")])
        out = a.assess("S1", 1, Q, FACTS)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["provisions"], [cid])
        self.assertEqual(out["citation_violations"], [])

    def test_a_model_that_returns_strings_where_lists_are_expected_is_handled(self):
        cid = self.retrieved_for("authority")[0]
        raw = {"finding": "f", "provisions": cid, "open_questions": "Is the server in the UAE?",
               "proposed_action": {"class": "withhold", "text": "t"}, "confidence": "medium"}
        out = self.agent("authority", [raw]).assess("S1", 1, Q, FACTS)
        self.assertEqual(out["provisions"], [cid])
        self.assertEqual(out["citation_violations"], [])
        self.assertEqual(out["open_questions"], ["Is the server in the UAE?"])

    def test_an_invented_chunk_id_is_stripped_recorded_and_lowers_confidence(self):
        a = self.agent("authority", [assessment_json(provisions=["UAE-FL2-2019:9999"], cls="share", confidence="high")])
        out = a.assess("S1", 1, Q, FACTS)
        self.assertEqual(out["provisions"], [])
        self.assertEqual(out["citation_violations"], ["UAE-FL2-2019:9999"])
        self.assertEqual(out["confidence"], "low")

    def test_a_real_chunk_that_was_not_retrieved_for_this_agent_is_also_stripped(self):
        outside = next(c["chunk_id"] for c in KB.chunks if c["source_id"] not in ROLES["authority"].scope)
        a = self.agent("authority", [assessment_json(provisions=[outside], cls="share")])
        out = a.assess("S1", 1, Q, FACTS)
        self.assertEqual(out["provisions"], [])
        self.assertEqual(out["citation_violations"], [outside])

    def test_failed_model_gives_an_escalation_not_a_crash(self):
        a = self.agent("clinic", [None, None])
        out = a.assess("S1", 1, Q, FACTS)
        self.assertEqual(out["status"], "model_unavailable")
        self.assertEqual(out["proposed_action"]["class"], "escalate_to_human")
        self.assertEqual(out["confidence"], "low")

    def test_unparseable_reply_is_asked_again_once(self):
        a = self.agent("clinic", ["I think maybe yes", assessment_json()])
        out = a.assess("S1", 1, Q, FACTS)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(self.model.calls, 2)

    def test_two_unparseable_replies_end_as_unavailable(self):
        a = self.agent("clinic", ["nope", "still nope"])
        self.assertEqual(a.assess("S1", 1, Q, FACTS)["status"], "model_unavailable")

    def test_an_unknown_action_class_becomes_escalate_to_human(self):
        a = self.agent("clinic", [assessment_json(cls="delete_everything")])
        out = a.assess("S1", 1, Q, FACTS)
        self.assertEqual(out["proposed_action"]["class"], "escalate_to_human")
        self.assertIn("escalate_to_human", ACTION_CLASSES)

    def test_prompt_shows_only_its_own_facts_and_the_document_status_caveat(self):
        a = self.agent("coach", [assessment_json()])
        out = a.assess("S1", 1, "Does the Dubai AI policy still apply?", ["SECRET-COACH-FACT"], messages=[])
        user = self.model.prompts[0]["user"]
        self.assertIn("SECRET-COACH-FACT", user)
        self.assertNotIn("SECRET-CLINIC-FACT", user)
        for cid in out["retrieved"]:
            self.assertIn(self.tool.get(cid)["version_status"], user, cid)

    def test_prompt_tells_the_model_to_cite_only_listed_ids_and_never_to_diagnose(self):
        a = self.agent("coach", [assessment_json()])
        a.assess("S1", 1, Q, FACTS)
        s = self.model.prompts[0]["system"].lower()
        self.assertIn("only", s)
        self.assertIn("chunk id", s)
        self.assertIn("diagnosis", s)

    def test_emergency_language_from_the_member_skips_the_model(self):
        a = self.agent("coach", [])
        out = a.assess("S1", 1, Q, FACTS, member_message="I have chest pain and my left arm is numb")
        self.assertEqual(out["status"], "emergency")
        self.assertEqual(self.model.calls, 0)
        self.assertEqual(out["proposed_action"]["class"], "emergency_redirect")
        self.assertIn("999", out["draft_reply_to_member"])

    def test_a_dose_in_the_coach_draft_reply_is_replaced_and_recorded(self):
        a = self.agent("coach", [assessment_json(draft_reply="Take 5000 IU of vitamin D every day.")])
        out = a.assess("S1", 1, Q, FACTS, member_message="my vitamin D is low")
        self.assertNotIn("5000", out["draft_reply_to_member"])
        self.assertIn("dose", out["guard"]["violations"])

    def test_a_non_string_draft_reply_does_not_crash_the_coach(self):
        for draft in (["not", "a", "string"], {"x": 1}, 42, True):
            a = self.agent("coach", [assessment_json(draft_reply=draft)])
            out = a.assess("S1", 1, Q, FACTS, member_message="my vitamin D is low")
            self.assertEqual(out["status"], "ok", draft)
            self.assertTrue(out["draft_reply_to_member"] is None or isinstance(out["draft_reply_to_member"], str), draft)
        a = self.agent("coach", [assessment_json(draft_reply=["not", "a", "string"])])
        self.assertEqual(a.assess("S1", 1, Q, FACTS)["draft_reply_to_member"], "not a string")
        a = self.agent("coach", [assessment_json(draft_reply={"x": 1})])
        self.assertIsNone(a.assess("S1", 1, Q, FACTS)["draft_reply_to_member"])

    def test_a_dose_in_a_list_draft_reply_is_still_replaced_and_recorded(self):
        a = self.agent("coach", [assessment_json(draft_reply=["Take 5000 IU", "of vitamin D every day."])])
        out = a.assess("S1", 1, Q, FACTS, member_message="my vitamin D is low")
        self.assertNotIn("5000", out["draft_reply_to_member"])
        self.assertIn("dose", out["guard"]["violations"])
        guards = [json.loads(l) for l in (Path(self.tmp.name) / "run.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertIn("dose", [v for r in guards if r["type"] == "guard" for v in r["payload"].get("output", [])])

    def test_a_null_or_blank_finding_is_asked_again_then_escalates(self):
        for bad in (None, "   ", 7, ["a"]):
            a = self.agent("clinic", [assessment_json(finding=bad), assessment_json(finding=bad)])
            out = a.assess("S1", 1, Q, FACTS)
            self.assertEqual(out["status"], "model_unavailable", bad)
            self.assertEqual(out["proposed_action"]["class"], "escalate_to_human", bad)
            self.assertNotIn("None", out["finding"], bad)
            self.assertEqual(self.model.calls, 2, bad)
        recs = [json.loads(l) for l in (Path(self.tmp.name) / "run.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(sum(r["type"] == "assessment_failed" for r in recs), 4)

    def test_a_null_finding_then_a_good_reply_is_used(self):
        a = self.agent("clinic", [assessment_json(finding=None), assessment_json(finding="The text says ...")])
        out = a.assess("S1", 1, Q, FACTS)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["finding"], "The text says ...")
        self.assertEqual(self.model.calls, 2)

    def test_only_the_coach_has_the_member_facing_guard(self):
        a = self.agent("clinic", [assessment_json()])
        out = a.assess("S1", 1, Q, FACTS, member_message="chest pain")
        self.assertNotEqual(out["status"], "emergency")


if __name__ == "__main__":
    unittest.main()
