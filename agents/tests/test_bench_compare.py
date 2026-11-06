import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import bench  # noqa: E402

ONE = {"q1": {"evidence": "strong", "top": [["A:0001", 20.0, 0.9]]}}


class CompareGolden(unittest.TestCase):
    def test_identical_files_have_no_differences(self):
        self.assertEqual(bench.compare_golden(ONE, dict(ONE)), [])

    def test_an_empty_golden_file_is_not_reported_as_identical(self):
        self.assertTrue(bench.compare_golden({}, ONE))

    def test_a_query_missing_from_the_new_run_is_a_difference_not_a_crash(self):
        want = {**ONE, "q2": {"evidence": "weak", "top": []}}
        self.assertIn("q2", bench.compare_golden(want, ONE))

    def test_a_query_that_is_only_in_the_new_run_is_a_difference(self):
        got = {**ONE, "q3": {"evidence": "none", "top": []}}
        self.assertIn("q3", bench.compare_golden(ONE, got))

    def test_a_changed_score_is_a_difference(self):
        got = {"q1": {"evidence": "strong", "top": [["A:0001", 19.0, 0.9]]}}
        self.assertEqual(bench.compare_golden(ONE, got), ["q1"])


if __name__ == "__main__":
    unittest.main()
