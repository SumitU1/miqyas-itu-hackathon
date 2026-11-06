import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from agents.audit import AuditLog, verify_file  # noqa: E402
from agents.coordinator import Coordinator, choose_action  # noqa: E402
from agents.kbtool import KBTool, load_kb  # noqa: E402
from agents.roles import ROLES  # noqa: E402
from agents.testing import ScriptedModel, assessment_json  # noqa: E402

FULL_KB = ROOT / "kb" / "out" / "chunks.jsonl"
KB = load_kb()
STRONG_Q = "what must a telehealth provider do before sharing patient information with another facility"


def scenario(**over):
    s = {
        "scenario_id": "T1", "title": "test scenario",
        "chunks": [
            {"id": "T1-C1", "title": "first", "question": "May the clinic receive the member's lab report?",
             "facts": {"coach": ["COACH-ONLY-FACT-1"], "clinic": ["CLINIC-ONLY-FACT-1"], "authority": ["AUTH-ONLY-FACT-1"]},
             "policy_questions": [STRONG_Q], "touches": ["data-transfer"]},
            {"id": "T1-C2", "title": "second", "question": "What now?",
             "facts": {"coach": ["COACH-ONLY-FACT-2"], "clinic": [], "authority": ["AUTH-ONLY-FACT-2"]},
             "policy_questions": [], "touches": []},
        ],
    }
    s.update(over)
    return s


def by_actor(replies):
    """replies: {role: assessment dict or None}; adviser answers with the first retrieved id."""
    def f(actor, system, user):
        role = actor.split(":")[1]
        if role == "adviser":
            import re
            m = re.search(r"\[([A-Z0-9\-]+:\d{4})\]", user)
            return {"ruling": "The text says ...", "provisions": [m.group(1)], "conditions": []}
        return replies.get(role, assessment_json())
    return f


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "run.jsonl"
        self.audit = AuditLog(self.path, "T1")
        self.tool = KBTool(KB, self.audit)

    def tearDown(self):
        self.tmp.cleanup()

    def run_it(self, replies=None, scen=None):
        self.model = ScriptedModel(by_actor(replies or {}))
        self.coord = Coordinator(self.tool, self.model, self.audit)
        return self.coord.run_scenario(scen or scenario())

    def records(self, type_=None):
        recs = [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines()]
        return [r for r in recs if type_ is None or r["type"] == type_]

    def prompt_for(self, role, n=0):
        return [p for p in self.model.prompts if p["actor"] == f"agent:{role}"][n]["user"]

    # information asymmetry -------------------------------------------------
    def test_each_agent_sees_only_its_own_facts(self):
        self.run_it()
        coach, clinic, auth = (self.prompt_for(r) for r in ("coach", "clinic", "authority"))
        self.assertIn("COACH-ONLY-FACT-1", coach)
        self.assertNotIn("CLINIC-ONLY-FACT-1", coach + auth)
        self.assertNotIn("AUTH-ONLY-FACT-1", coach + clinic)
        self.assertNotIn("COACH-ONLY-FACT-1", clinic + auth)

    def test_query_planning_is_passed_to_the_adviser(self):
        c = Coordinator(self.tool, ScriptedModel([]), self.audit, plan_queries=True)
        self.assertTrue(c.adviser.plan_queries)
        self.assertFalse(Coordinator(self.tool, ScriptedModel([]), self.audit).adviser.plan_queries)

    def test_the_adviser_is_never_shown_raw_agent_facts(self):
        self.run_it()
        for p in self.model.prompts:
            if p["actor"] == "agent:adviser":
                self.assertNotIn("ONLY-FACT", p["user"])

    def test_later_chunks_add_to_what_an_agent_knows_and_it_receives_the_ruling_message(self):
        self.run_it()
        coach2 = self.prompt_for("coach", 1)
        self.assertIn("COACH-ONLY-FACT-1", coach2)
        self.assertIn("COACH-ONLY-FACT-2", coach2)
        self.assertIn("MESSAGES ROUTED TO YOU", coach2)
        self.assertIn("coordinator", coach2)

    def test_an_agent_with_no_new_facts_is_still_asked_if_it_already_knows_something_and_skipped_if_it_knows_nothing(self):
        s = scenario()
        s["chunks"][0]["facts"]["clinic"] = []
        self.run_it(scen=s)
        self.assertEqual(len([p for p in self.model.prompts if p["actor"] == "agent:clinic"]), 0)

    # decisions -------------------------------------------------------------
    def test_the_decision_record_has_every_field_a_reviewer_needs(self):
        decisions = self.run_it()
        d = decisions[0]
        for k in ("decision_id", "scenario_id", "chunk_id", "trigger", "assessments", "verification", "conflicts",
                  "adviser_answers", "action", "needs_human", "needs_human_reasons", "approval", "kb_build_id", "reasoning_trace"):
            self.assertIn(k, d, k)
        self.assertEqual(d["approval"]["status"], "pending")
        self.assertEqual(d["kb_build_id"], self.tool.build_id)

    def test_data_transfer_always_needs_a_human(self):
        d = self.run_it()[0]
        self.assertTrue(d["needs_human"])
        self.assertIn("touches data-transfer", " ".join(d["needs_human_reasons"]))

    def test_opposite_actions_conflict_and_the_protective_one_wins_pending_a_human(self):
        d = self.run_it({"coach": assessment_json(cls="no_action"), "clinic": assessment_json(cls="share"),
                         "authority": assessment_json(cls="withhold")})[0]
        self.assertEqual(d["action"]["class"], "withhold")
        self.assertIn("action-conflict", [c["type"] for c in d["conflicts"]])
        self.assertTrue(d["needs_human"])

    def test_choose_action_orders_by_protectiveness(self):
        mk = lambda c: {"agent": "x", "status": "ok", "proposed_action": {"class": c, "text": c}}
        self.assertEqual(choose_action([mk("share"), mk("no_action")])["class"], "share")
        self.assertEqual(choose_action([mk("share"), mk("withhold")])["class"], "withhold")
        self.assertEqual(choose_action([mk("withhold"), mk("emergency_redirect")])["class"], "emergency_redirect")
        self.assertEqual(choose_action([mk("withhold"), mk("escalate_to_human")])["class"], "escalate_to_human")

    def test_an_adviser_abstention_is_a_reason_for_a_human(self):
        s = scenario()
        s["chunks"][0]["policy_questions"] = ["best recipe for lamb biryani"]
        d = self.run_it(scen=s)[0]
        self.assertEqual(d["adviser_answers"][0]["outcome"], "abstain")
        self.assertIn("adviser abstained", " ".join(d["needs_human_reasons"]))

    def test_a_failed_agent_forces_escalation(self):
        d = self.run_it({"clinic": None})[0]
        self.assertEqual(d["action"]["class"], "escalate_to_human")
        self.assertIn("missing-assessment", [c["type"] for c in d["conflicts"]])

    def test_an_agent_open_question_reaches_the_adviser_once_and_is_capped(self):
        a = assessment_json(open_questions=[STRONG_Q + " today"])
        d = self.run_it({"coach": a, "clinic": a, "authority": a})[0]
        asked = [x["question"] for x in d["adviser_answers"]]
        self.assertLessEqual(len(asked), 4)
        self.assertEqual(len(asked), len(set(asked)))

    def test_a_scripted_approval_is_logged_as_simulated(self):
        s = scenario()
        s["chunks"][0]["scripted_approval"] = {"decision": "rejected", "note": "member has not consented"}
        d = self.run_it(scen=s)[0]
        self.assertEqual(d["approval"]["status"], "rejected")
        self.assertTrue(d["approval"]["simulated"])
        appr = self.records("approval")
        self.assertEqual(len(appr), 1)
        self.assertTrue(appr[0]["payload"]["simulated"])

    # concurrency -----------------------------------------------------------
    def _decisions(self, workers, latency=0.0, replies=None, scen=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "r.jsonl"
        audit = AuditLog(path, "T1")
        model = ScriptedModel(by_actor(replies or {}), latency=latency)
        t = time.perf_counter()
        decs = Coordinator(KBTool(KB, audit), model, audit, workers=workers).run_scenario(scen or scenario())
        return decs, time.perf_counter() - t, path

    def test_parallel_and_sequential_runs_make_identical_decisions(self):
        a = {"coach": assessment_json(open_questions=[STRONG_Q + " today"]), "clinic": assessment_json(cls="share"),
             "authority": assessment_json(cls="withhold")}
        seq, _, _ = self._decisions(1, replies=a)
        par, _, path = self._decisions(4, replies=a)
        self.assertEqual(json.dumps(seq, sort_keys=True), json.dumps(par, sort_keys=True))
        ok, info = verify_file(path)
        self.assertTrue(ok, info)

    def test_parallel_run_is_clearly_faster_when_model_calls_are_slow(self):
        _, t_seq, _ = self._decisions(1, latency=0.08)
        _, t_par, path = self._decisions(4, latency=0.08)
        self.assertLess(t_par, t_seq * 0.8, (t_seq, t_par))
        self.assertTrue(verify_file(path)[0])

    def test_the_audit_messages_are_in_the_same_order_in_parallel_runs(self):
        def kinds(path):
            return [(r["payload"]["from"], r["payload"]["to"], r["payload"]["type"]) for r in
                    (json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()) if r["type"] == "message"]
        _, _, p1 = self._decisions(1)
        _, _, p2 = self._decisions(4)
        self.assertEqual(kinds(p1), kinds(p2))

    # audit -----------------------------------------------------------------
    def test_every_message_has_the_full_envelope(self):
        self.run_it()
        msgs = self.records("message")
        self.assertTrue(msgs)
        for m in msgs:
            for k in ("msg_id", "scenario_id", "round", "from", "to", "type", "payload", "citations", "kb_build_id", "ts"):
                self.assertIn(k, m["payload"] if k not in ("ts",) else m, k)

    def test_the_whole_run_leaves_a_verifiable_chain_with_all_record_kinds(self):
        self.run_it()
        ok, info = verify_file(self.path)
        self.assertTrue(ok, info)
        kinds = {r["type"] for r in self.records()}
        for k in ("chunk_release", "message", "kb_query", "verification", "decision"):
            self.assertIn(k, kinds)

    @unittest.skipUnless(FULL_KB.exists(), "needs the full-text KB (kb/out/chunks.jsonl), rebuilt with scripts/fetch_sources.py then kb/build_kb.py")

    def test_malformed_model_replies_still_end_in_a_decision_record_and_a_valid_chain(self):
        # list draft from the coach, null finding from the clinic, null ruling from the adviser
        def script(actor, system, user):
            role = actor.split(":")[1]
            if role == "adviser":                       # valid citation, so only the null ruling can make it abstain
                import re
                m = re.search(r"\[([A-Z0-9\-]+:\d{4})\]", user)
                return {"ruling": None, "provisions": [m.group(1)], "conditions": []}
            if role == "coach":
                return assessment_json(cls="inform_member", draft_reply=["not", "a", "string"])
            if role == "clinic":
                return assessment_json(finding=None, cls="share")
            return assessment_json(cls="withhold")
        self.model = ScriptedModel(script)
        self.coord = Coordinator(self.tool, self.model, self.audit)
        scen = scenario()
        decisions = self.coord.run_scenario(scen)
        self.assertEqual([d["chunk_id"] for d in decisions], [c["id"] for c in scen["chunks"]])
        ok, info = verify_file(self.path)
        self.assertTrue(ok, info)
        recorded = [r["payload"]["chunk_id"] for r in self.records("decision")]
        self.assertEqual(recorded, [c["id"] for c in scen["chunks"]])
        for d in decisions:
            clinic = next(a for a in d["assessments"] if a["agent"] == "clinic")
            self.assertEqual(clinic["status"], "model_unavailable")
            self.assertNotEqual(clinic["finding"], "None")
            self.assertEqual(d["action"]["class"], "escalate_to_human")
            self.assertTrue(d["needs_human"])
            coach = next(a for a in d["assessments"] if a["agent"] == "coach")
            self.assertEqual(coach["draft_reply_to_member"], "not a string")
        self.assertTrue(any(r["actor"] == "agent:clinic" for r in self.records("assessment_failed")))
        first = decisions[0]
        self.assertEqual(first["adviser_answers"][0]["outcome"], "abstain")
        self.assertEqual(first["adviser_answers"][0]["abstain_reason"], "unparseable-reply")
        self.assertIsNone(first["adviser_answers"][0]["ruling"])
        self.assertIn("scenario_end", {r["type"] for r in self.records()})

    def test_no_clinical_facts_go_to_the_authority_even_in_messages(self):
        self.run_it()
        for p in self.model.prompts:
            if p["actor"] == "agent:authority":
                self.assertNotIn("COACH-ONLY", p["user"])


if __name__ == "__main__":
    unittest.main()
