import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.audit import AuditLog  # noqa: E402
from agents.verify_log import main  # noqa: E402


def run(args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        rc = main(args)
    return rc, out.getvalue()


def run_both(args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = main(args)
    return rc, out.getvalue(), err.getvalue()


class VerifyCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name) / "a.jsonl"
        log = AuditLog(self.p, "t")
        for i in range(3):
            log.append("message", "x", {"i": i})
        self.head = log.head_hash

    def tearDown(self):
        self.tmp.cleanup()

    def test_good_log_exits_zero_and_prints_the_head(self):
        rc, out = run([str(self.p)])
        self.assertEqual(rc, 0)
        self.assertIn(self.head, out)
        self.assertIn("3 records", out)

    def test_expected_head_catches_a_cut_tail(self):
        lines = self.p.read_text(encoding="utf-8").splitlines()[:-1]
        self.p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.assertEqual(run([str(self.p)])[0], 0)
        rc, out = run([str(self.p), "--head", self.head])
        self.assertEqual(rc, 1)
        self.assertIn("FAILS", out)

    def test_edit_exits_one(self):
        lines = self.p.read_text(encoding="utf-8").splitlines()
        rec = json.loads(lines[1]); rec["payload"]["i"] = 9; lines[1] = json.dumps(rec)
        self.p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        rc, out = run([str(self.p)])
        self.assertEqual(rc, 1)
        self.assertIn("record 1", out)

    def test_good_log_output_line_is_unchanged(self):
        rc, out, _ = run_both([str(self.p), "--head", self.head])
        self.assertEqual(rc, 0)
        self.assertEqual(out, f"chain verified: 3 records, head {self.head}\n")

    def test_missing_path_exits_two_with_one_line(self):
        rc, out, err = run_both([str(Path(self.tmp.name) / "nope.jsonl")])
        self.assertEqual(rc, 2)
        self.assertNotIn("verified", out + err)
        self.assertEqual(len(err.strip().splitlines()), 1, err)
        self.assertIn("nope.jsonl", err)

    def test_directory_path_exits_two(self):
        rc, out, err = run_both([self.tmp.name])
        self.assertEqual(rc, 2)
        self.assertNotIn("verified", out + err)

    def test_empty_file_exits_one_with_no_records(self):
        empty = Path(self.tmp.name) / "empty.jsonl"
        empty.write_bytes(b"")
        rc, out, err = run_both([str(empty)])
        self.assertEqual(rc, 1)
        self.assertIn("no records", out + err)
        self.assertNotIn("verified", out)
        self.assertEqual(run([str(empty), "--head", self.head])[0], 1)

    def test_garbage_file_fails_with_a_reason_not_a_traceback(self):
        junk = Path(self.tmp.name) / "junk.jsonl"
        for data in (b"\x80\x81\x00\xff", b"[1,2]\n", b"5\n", b'{"seq":0,"prev_hash":"' + b"0" * 64 + b'"}\n'):
            junk.write_bytes(data)
            rc, out = run([str(junk)])
            self.assertEqual(rc, 1, data)
            self.assertIn("FAILS", out)

    def test_without_head_a_warning_goes_to_stderr_and_exit_is_unchanged(self):
        rc, out, err = run_both([str(self.p)])
        self.assertEqual(rc, 0)
        self.assertIn("--head", err)
        rc, out, err = run_both([str(self.p), "--head", self.head])
        self.assertEqual(err, "")


if __name__ == "__main__":
    unittest.main()
