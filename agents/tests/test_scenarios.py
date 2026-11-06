import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from agents.scenario import load_scenarios, validate_scenario  # noqa: E402


def good():
    return {"scenario_id": "S0", "title": "t", "synthetic": True, "member": {"alias": "Member A (synthetic)"},
            "chunks": [{"id": "S0-C1", "title": "c", "question": "q?", "facts": {"coach": ["f"]}, "policy_questions": ["p?"]}]}


class Validation(unittest.TestCase):
    def test_a_good_scenario_has_no_errors(self):
        self.assertEqual(validate_scenario(good()), [])

    def test_scenario_id_must_be_a_safe_folder_name(self):
        for bad in ("../x", "a/b", "a\\b", "", "x" * 41, "S 1", "S1\n"):
            s = good(); s["scenario_id"] = bad
            self.assertTrue(any("scenario_id" in e for e in validate_scenario(s)), repr(bad))
        s = good(); s["scenario_id"] = "S3-extra_1"
        self.assertEqual(validate_scenario(s), [])

    def test_must_be_marked_synthetic(self):
        s = good(); s["synthetic"] = False
        self.assertTrue(any("synthetic" in e for e in validate_scenario(s)))

    def test_unknown_role_in_facts_is_an_error(self):
        s = good(); s["chunks"][0]["facts"]["adviser"] = ["x"]
        self.assertTrue(any("adviser" in e for e in validate_scenario(s)))

    def test_duplicate_chunk_ids_and_missing_fields_are_errors(self):
        s = good(); s["chunks"].append(dict(s["chunks"][0]))
        self.assertTrue(any("duplicate" in e for e in validate_scenario(s)))
        s2 = good(); del s2["chunks"][0]["question"]
        self.assertTrue(any("question" in e for e in validate_scenario(s2)))

    def test_facts_must_be_lists_of_strings_not_a_bare_string(self):
        s = good(); s["chunks"][0]["facts"]["coach"] = "one long fact"
        self.assertTrue(any("facts" in e and "list" in e for e in validate_scenario(s)))
        s = good(); s["chunks"][0]["facts"]["coach"] = ["ok", ""]
        self.assertTrue(any("empty" in e for e in validate_scenario(s)))

    def test_a_per_role_question_needs_a_default_or_every_role_that_gets_facts(self):
        s = good(); s["chunks"][0]["question"] = {"clinic": "q for clinic?"}
        self.assertTrue(any("question" in e and "coach" in e for e in validate_scenario(s)))
        s["chunks"][0]["question"]["default"] = "q?"
        self.assertEqual(validate_scenario(s), [])

    def test_a_blank_question_and_non_list_policy_questions_are_errors(self):
        s = good(); s["chunks"][0]["question"] = "  "
        self.assertTrue(any("question" in e for e in validate_scenario(s)))
        s = good(); s["chunks"][0]["policy_questions"] = "one question?"
        self.assertTrue(any("policy_questions" in e for e in validate_scenario(s)))

    def test_looks_like_real_personal_data_is_rejected(self):
        s = good(); s["chunks"][0]["facts"]["coach"] = ["Emirates ID 784-1990-1234567-1"]
        self.assertTrue(any("identifier" in e for e in validate_scenario(s)))
        s = good(); s["chunks"][0]["facts"]["coach"] = ["call me on +971 50 123 4567 or a@b.com"]
        self.assertTrue(any("identifier" in e for e in validate_scenario(s)))


class ShippedScenarios(unittest.TestCase):
    def test_the_shipped_scenarios_are_valid_and_cover_the_four_planned_situations(self):
        scs = load_scenarios(ROOT / "scenarios")
        self.assertGreaterEqual(len(scs), 4)
        for s in scs:
            self.assertEqual(validate_scenario(s), [], s["scenario_id"])
            self.assertGreaterEqual(len(s["chunks"]), 3, "sequenced chunks")
            self.assertTrue(any(c.get("incomplete") for c in s["chunks"]), "each scenario releases incomplete information")
            roles = {r for c in s["chunks"] for r in c["facts"] if c["facts"][r]}
            self.assertGreaterEqual(len(roles), 2, "uneven information across agents")

    def test_no_chunk_hands_the_same_fact_to_two_agents_verbatim(self):
        for s in load_scenarios(ROOT / "scenarios"):
            seen = {}
            for c in s["chunks"]:
                for role, facts in c["facts"].items():
                    for f in facts:
                        self.assertNotIn(f, seen, f"{s['scenario_id']}: fact given to {seen.get(f)} and {role}")
                        seen[f] = role


if __name__ == "__main__":
    unittest.main()
