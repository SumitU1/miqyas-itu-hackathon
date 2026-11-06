import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from agents.audit import AuditLog  # noqa: E402
from agents.coordinator import Coordinator  # noqa: E402
from agents.kbtool import KBTool, load_kb  # noqa: E402
from agents.testing import ScriptedModel, assessment_json  # noqa: E402
from agents.trace import build_trace  # noqa: E402
from agents.tests.test_coordinator import by_actor, scenario  # noqa: E402

KB = load_kb()


class TraceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "run.jsonl"
        audit = AuditLog(self.path, "T1")
        tool = KBTool(KB, audit)
        import re
        base = by_actor({})
        seen = {}

        def script(actor, system, user):
            if actor == "agent:clinic":
                cid = re.search(r"\[([A-Z0-9\-]+:\d{4})\]", user).group(1)   # cite the first passage it was shown
                seen["cid"] = cid
                return assessment_json(finding="Sharing patient information between facilities and consent.",
                                       provisions=[cid], cls="withhold")
            if actor == "agent:coach":
                return assessment_json(finding="Coach finding.", cls="inform_member", draft_reply="Please book a visit with your doctor today.")
            return base(actor, system, user)

        model = ScriptedModel(script)
        s = scenario()
        s["chunks"][0]["scripted_approval"] = {"decision": "approved", "note": "ok"}
        Coordinator(tool, model, audit).run_scenario(s)
        self.cid = seen["cid"]
        self.md = build_trace(self.path, KB)

    def tearDown(self):
        self.tmp.cleanup()

    def test_header_states_that_the_chain_verifies(self):
        self.assertIn("chain verified", self.md.lower())

    def test_each_decision_shows_trigger_assessments_citation_ruling_and_approval(self):
        for needle in ("T1-C1-D", "first", "clinic", self.cid, "http", "PDF p", "Adviser", "approved", "simulated"):
            self.assertIn(needle, self.md, needle)

    def test_the_coach_draft_reply_after_the_guard_is_shown(self):
        self.assertIn("Please book a visit with your doctor today.", self.md)

    def test_the_query_the_adviser_actually_used_is_shown(self):
        self.assertIn("query used", self.md.lower())

    def test_it_states_what_the_reasoning_trace_is(self):
        self.assertIn("stated rationale", self.md)

    def test_a_unicode_line_separator_in_a_payload_still_renders_as_verified(self):
        AuditLog(self.path, "T1").append("message", "agent:coach", {"note": "line sep and next\u0085line"})
        md = build_trace(self.path, KB)
        self.assertIn("chain verified", md.lower())
        self.assertNotIn("FAILS", md)

    def test_a_tampered_log_is_reported_not_rendered_as_trustworthy(self):
        lines = self.path.read_text(encoding="utf-8").splitlines()
        rec = json.loads(lines[3])
        rec["payload"] = {"tampered": True}
        lines[3] = json.dumps(rec)
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        md = build_trace(self.path, KB)
        self.assertIn("FAILS", md)
        self.assertNotIn("chain verified", md.lower())


if __name__ == "__main__":
    unittest.main()
