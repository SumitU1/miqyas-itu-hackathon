import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from agents.audit import verify_file  # noqa: E402
from agents.run_scenarios import main, run_scenario_file  # noqa: E402
from agents.testing import ScriptedModel  # noqa: E402
from agents.tests.test_coordinator import by_actor  # noqa: E402


class RunnerTests(unittest.TestCase):
    def test_a_run_writes_log_trace_decisions_and_summary_and_the_chain_verifies(self):
        with tempfile.TemporaryDirectory() as d:
            model = ScriptedModel(by_actor({}))
            summary = run_scenario_file(ROOT / "scenarios" / "S3_clinic_record_sharing.json", Path(d), lambda audit: model)
            out = Path(d) / "S3"
            for f in ("audit.jsonl", "trace.md", "decisions.json", "summary.json"):
                self.assertTrue((out / f).exists(), f)
            ok, info = verify_file(out / "audit.jsonl", expected_head=summary["head_hash"])
            self.assertTrue(ok, info)
            self.assertEqual(summary["decisions"], 3)
            self.assertEqual(summary["synthetic"], True)
            self.assertIn("kb_build_id", summary)
            self.assertEqual(len(json.loads((out / "decisions.json").read_text(encoding="utf-8"))), 3)

    def test_rerunning_into_the_same_folder_starts_a_fresh_log_instead_of_appending(self):
        with tempfile.TemporaryDirectory() as d:
            for _ in range(2):
                run_scenario_file(ROOT / "scenarios" / "S3_clinic_record_sharing.json", Path(d), lambda a: ScriptedModel(by_actor({})))
            ok, info = verify_file(Path(d) / "S3" / "audit.jsonl")
            self.assertTrue(ok)
            starts = [l for l in (Path(d) / "S3" / "audit.jsonl").read_text(encoding="utf-8").splitlines() if '"scenario_start"' in l]
            self.assertEqual(len(starts), 1)


    def test_two_runs_in_the_same_second_both_keep_their_evidence(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("agents.run_scenarios.time.strftime", return_value="20261031T120000"):
                for _ in range(3):
                    run_scenario_file(ROOT / "scenarios" / "S3_clinic_record_sharing.json", Path(d), lambda a: ScriptedModel(by_actor({})))
            kept = sorted(p.name for p in (Path(d) / "S3").glob("audit.*.previous.jsonl"))
            self.assertEqual(len(kept), 2, kept)

    # command line ----------------------------------------------------------
    @staticmethod
    def _model(audit=None):
        inner = by_actor({})

        def f(actor, system, user):
            if actor == "agent:adviser" and "PASSAGES" not in user:      # the query-planning call
                return {"queries": ["patient consent sharing health information"]}
            return inner(actor, system, user)
        return ScriptedModel(f)

    def _cli(self, argv, env=None, factory=None):
        out, err = io.StringIO(), io.StringIO()
        old = dict(os.environ)
        try:
            for k in ("GATEWAY_LLM_KEY", "GATEWAY_ENV_FILE"):
                os.environ.pop(k, None)
            os.environ.update(env or {})
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = main(argv, model_factory=factory)
        finally:
            os.environ.clear()
            os.environ.update(old)
        return rc, out.getvalue(), err.getvalue()

    def test_no_scenario_and_no_all_flag_is_a_usage_error_not_a_silent_success(self):
        rc, _, err = self._cli([], factory=self._model)
        self.assertEqual(rc, 2)
        self.assertIn("--all", err)

    def test_a_missing_gateway_key_is_a_one_line_message_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out, err = self._cli([str(ROOT / "scenarios" / "S3_clinic_record_sharing.json"), "--out", d],
                                     env={"GATEWAY_ENV_FILE": str(Path(d) / "nope.env")})
        self.assertEqual(rc, 2)
        self.assertIn("gateway key", err)
        self.assertNotIn("Traceback", err)

    def test_a_missing_scenario_file_is_named_in_the_message(self):
        with tempfile.TemporaryDirectory() as d:
            rc, _, err = self._cli([str(Path(d) / "S9.json"), "--out", d], factory=self._model)
        self.assertEqual(rc, 2)
        self.assertIn("S9.json", err)
        self.assertNotIn("Traceback", err)

    def test_all_scenarios_can_run_side_by_side_and_each_chain_verifies(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out, err = self._cli(["--all", "--out", d, "--jobs", "4", "--workers", "2"],
                                     factory=self._model)
            self.assertEqual(rc, 0, err)
            for sid in ("S1", "S2", "S3", "S4"):
                ok, info = verify_file(next((Path(d) / sid).glob("audit.jsonl")))
                self.assertTrue(ok, info)
            self.assertEqual([l.split(":")[0] for l in out.splitlines() if l[:1] == "S"], ["S1", "S2", "S3", "S4"])

    def test_one_bad_scenario_does_not_hide_the_results_of_the_others(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "S9_bad.json"
            bad.write_text("{}", encoding="utf-8")
            rc, out, err = self._cli([str(ROOT / "scenarios" / "S3_clinic_record_sharing.json"), str(bad),
                                      "--out", d, "--jobs", "2"], factory=self._model)
            self.assertEqual(rc, 1, err)
            self.assertIn("S3:", out)                         # the good scenario is still reported
            self.assertIn("S9_bad.json", out + err)           # the bad one is named
            self.assertNotIn("Traceback", err)
            ok, info = verify_file(Path(d) / "S3" / "audit.jsonl")
            self.assertTrue(ok, info)

    def test_summary_counts_records_whose_payload_holds_a_unicode_line_separator(self):
        from agents.audit import AuditLog
        from agents.run_scenarios import summarise
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "audit.jsonl"
            log = AuditLog(p, "t")
            log.model_call("agent:coach", "auto", "h", ok=True, served_model="m")
            log.append("guard", "agent:coach", {"note": "a b\u0085c"})
            s = summarise([], p, {"scenario_id": "X", "title": "x", "synthetic": True})
            self.assertTrue(s["chain_verified"])
            self.assertEqual((s["audit_records"], s["guard_events"], s["model_calls"]), (2, 1, 1))


if __name__ == "__main__":
    unittest.main()
