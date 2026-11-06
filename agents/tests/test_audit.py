"""Tests for the hash-chained audit log.  Run:  python -m unittest discover -s agents/tests -v"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from agents.audit import GENESIS, AuditLog, verify_file  # noqa: E402


class AuditLogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "run.jsonl"
        self.log = AuditLog(self.path, run_id="t1")

    def tearDown(self):
        self.tmp.cleanup()

    def fill(self, n=4):
        for i in range(n):
            self.log.append("message", "coordinator", {"i": i})

    def lines(self):
        return [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines()]

    def test_first_record_points_at_genesis_and_each_record_at_the_previous_hash(self):
        self.fill(3)
        recs = self.lines()
        self.assertEqual(recs[0]["prev_hash"], GENESIS)
        self.assertEqual(recs[1]["prev_hash"], recs[0]["hash"])
        self.assertEqual(recs[2]["prev_hash"], recs[1]["hash"])
        self.assertEqual([r["seq"] for r in recs], [0, 1, 2])

    def test_untouched_log_verifies(self):
        self.fill()
        ok, info = verify_file(self.path)
        self.assertTrue(ok, info)
        self.assertEqual(info["records"], 4)

    def test_edited_payload_is_detected_at_that_record(self):
        self.fill()
        recs = self.lines()
        recs[2]["payload"]["i"] = 99
        self.path.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
        ok, info = verify_file(self.path)
        self.assertFalse(ok)
        self.assertEqual(info["bad_seq"], 2)
        self.assertIn("hash", info["reason"])

    def test_deleted_middle_record_is_detected(self):
        self.fill()
        recs = self.lines()
        del recs[1]
        self.path.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
        ok, info = verify_file(self.path)
        self.assertFalse(ok)

    def test_reordered_records_are_detected(self):
        self.fill()
        recs = self.lines()
        recs[1], recs[2] = recs[2], recs[1]
        self.path.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
        ok, _ = verify_file(self.path)
        self.assertFalse(ok)

    def test_recomputed_hash_after_edit_still_breaks_the_next_link(self):
        """An editor who also fixes the edited record's own hash is caught by the next record's prev_hash."""
        self.fill()
        recs = self.lines()
        recs[1]["payload"]["i"] = 77
        from agents.audit import record_hash
        recs[1]["hash"] = record_hash(recs[1])
        self.path.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
        ok, info = verify_file(self.path)
        self.assertFalse(ok)
        self.assertEqual(info["bad_seq"], 2)

    def test_truncated_tail_is_only_detected_against_the_published_head_hash(self):
        self.fill()
        head = self.log.head_hash
        recs = self.lines()[:-1]
        self.path.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
        ok, _ = verify_file(self.path)
        self.assertTrue(ok, "a chain alone cannot see a cut tail")
        ok, info = verify_file(self.path, expected_head=head)
        self.assertFalse(ok)
        self.assertIn("head", info["reason"])

    def test_reopening_a_log_continues_the_chain(self):
        self.fill(2)
        again = AuditLog(self.path, run_id="t1")
        again.append("message", "coordinator", {"i": 2})
        ok, info = verify_file(self.path)
        self.assertTrue(ok, info)
        self.assertEqual(info["records"], 3)

    def test_opening_a_tampered_log_refuses_to_append(self):
        self.fill(2)
        recs = self.lines()
        recs[0]["payload"]["i"] = 5
        self.path.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            AuditLog(self.path, run_id="t1")

    def test_concurrent_appends_from_many_threads_keep_one_valid_chain(self):
        import threading

        def work(k):
            for i in range(40):
                self.log.append("message", f"t{k}", {"k": k, "i": i})

        threads = [threading.Thread(target=work, args=(k,)) for k in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        ok, info = verify_file(self.path)
        self.assertTrue(ok, info)
        self.assertEqual(info["records"], 320)
        per_thread = {}
        for r in self.lines():
            per_thread.setdefault(r["actor"], []).append(r["payload"]["i"])
        for seq in per_thread.values():
            self.assertEqual(seq, sorted(seq), "each thread's own records stay in order")

    def test_kb_query_and_model_call_helpers_record_the_fields_the_brief_asks_for(self):
        self.log.kb_query("agent:adviser", "may data leave the UAE", ["UAE-FL2-2019:0010"], [11.2], "weak", "20261026T1648Z")
        self.log.model_call("agent:coach", "auto", "abc123", ok=True)
        recs = self.lines()
        self.assertEqual(recs[0]["type"], "kb_query")
        self.assertEqual(recs[0]["payload"]["chunk_ids"], ["UAE-FL2-2019:0010"])
        self.assertEqual(recs[0]["payload"]["evidence"], "weak")
        self.assertEqual(recs[1]["type"], "model_call")
        self.assertEqual(recs[1]["payload"]["prompt_hash"], "abc123")
        self.assertNotIn("api_key", json.dumps(recs))


class AuditReadRobustness(unittest.TestCase):
    """Reading a log never raises on bad content, and only real line ends delimit records."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "run.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_unicode_line_separators_inside_a_payload_do_not_break_the_chain(self):
        log = AuditLog(self.path, run_id="t1")
        log.append("message", "agent:coach", {"finding": "a b", "ruling": "c\u0085d", "x": "e f\x1cg"})
        raw = self.path.read_text(encoding="utf-8")
        self.assertIn(" ", raw)                       # written raw (ensure_ascii=False), not escaped
        self.assertIn("\u0085", raw)
        ok, info = verify_file(self.path)
        self.assertTrue(ok, info)
        self.assertEqual(info["records"], 1)
        again = AuditLog(self.path, run_id="t1")           # reopening must not refuse to append
        again.append("message", "coordinator", {"i": 1})
        ok, info = verify_file(self.path, expected_head=again.head_hash)
        self.assertTrue(ok, info)
        self.assertEqual(info["records"], 2)

    def test_crlf_and_blank_lines_still_verify(self):
        log = AuditLog(self.path, run_id="t1")
        for i in range(3):
            log.append("message", "x", {"i": i, "s": "p q"})
        lines = self.path.read_text(encoding="utf-8").split("\n")
        self.path.write_bytes("\r\n\r\n".join(lines).encode("utf-8"))
        ok, info = verify_file(self.path, expected_head=log.head_hash)
        self.assertTrue(ok, info)
        self.assertEqual(info["records"], 3)
        self.path.write_bytes("\r".join(lines).encode("utf-8"))   # lone CR line ends, as read_text always accepted
        ok, info = verify_file(self.path, expected_head=log.head_hash)
        self.assertTrue(ok, info)
        self.assertEqual(info["records"], 3)

    def assertFailsCleanly(self, data: bytes, bad_seq=0):
        self.path.write_bytes(data)
        ok, info = verify_file(self.path)                  # must not raise
        self.assertFalse(ok)
        self.assertEqual(info["bad_seq"], bad_seq)
        self.assertTrue(info["reason"])
        return info

    def test_bytes_that_are_not_utf8_fail_with_a_reason(self):
        info = self.assertFailsCleanly(b"\x80\x81\n")
        self.assertIn("UTF-8", info["reason"])

    def test_bad_utf8_is_located_at_its_record(self):
        log = AuditLog(self.path, run_id="t1")
        log.append("message", "x", {"i": 0})
        good = self.path.read_bytes()
        info = self.assertFailsCleanly(good + b"\xff\xfe garbage\n", bad_seq=1)
        self.assertIn("UTF-8", info["reason"])

    def test_a_json_list_line_fails_with_a_reason(self):
        info = self.assertFailsCleanly(b"[1,2]\n")
        self.assertIn("object", info["reason"])

    def test_a_json_number_line_fails_with_a_reason(self):
        self.assertFailsCleanly(b"5\n")

    def test_a_record_missing_hashed_fields_fails_with_a_reason(self):
        rec = {"seq": 0, "prev_hash": GENESIS, "hash": "x"}
        info = self.assertFailsCleanly((json.dumps(rec) + "\n").encode("utf-8"))
        self.assertIn("run_id", info["reason"])

    def test_opening_a_garbage_log_refuses_to_append_with_value_error(self):
        self.path.write_bytes(b"[1,2]\n")
        with self.assertRaises(ValueError):
            AuditLog(self.path, run_id="t1")


if __name__ == "__main__":
    unittest.main()
