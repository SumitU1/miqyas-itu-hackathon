import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SEARCH = ROOT / "kb" / "search.py"


def run(*args):
    return subprocess.run([sys.executable, "-I", str(SEARCH), *args], capture_output=True, text=True, encoding="utf-8", timeout=120)


class SearchCli(unittest.TestCase):
    def test_a_zero_or_negative_result_count_is_a_usage_error(self):
        for k in ("0", "-1"):
            r = run("consent", "-k", k)
            self.assertEqual(r.returncode, 2, (k, r.stdout[:200], r.stderr[:200]))
            self.assertIn("-k", r.stderr)
            self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
