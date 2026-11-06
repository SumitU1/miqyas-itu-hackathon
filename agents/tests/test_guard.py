import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.guard import SAFE_REPLACEMENT, input_guard, output_guard  # noqa: E402


class InputGuard(unittest.TestCase):
    def test_emergency_phrases_skip_the_model_and_point_to_emergency_services(self):
        for t in ["I have crushing chest pain and my arm is numb", "I can't breathe", "I want to kill myself",
                  "my father is unconscious", "she took an overdose", "sudden weakness one side of the face, speech slurred"]:
            r = input_guard(t)
            self.assertEqual(r["action"], "emergency", t)
            self.assertIn("999", r["reply"])
            self.assertIn("998", r["reply"])

    def test_ordinary_questions_pass(self):
        for t in ["Why is my LDL a bit high?", "Share my sleep data with the clinic", "What does ferritin measure?"]:
            self.assertEqual(input_guard(t)["action"], "pass", t)


class OutputGuard(unittest.TestCase):
    def test_a_dose_instruction_is_blocked(self):
        for t in ["Take 500 mg of metformin twice a day.", "You should take 2000 IU vitamin D daily", "increase your dose to 10 mg"]:
            r = output_guard(t)
            self.assertFalse(r["ok"], t)
            self.assertIn("dose", r["violations"])
            self.assertNotIn("500", r["text"])

    def test_a_diagnosis_is_blocked(self):
        for t in ["You have type 2 diabetes.", "This means you are suffering from anaemia", "You were diagnosed with hypothyroidism"]:
            r = output_guard(t)
            self.assertFalse(r["ok"], t)
            self.assertIn("diagnosis", r["violations"])

    def test_a_guarantee_is_blocked(self):
        self.assertIn("guarantee", output_guard("This plan is guaranteed to lower your cholesterol")["violations"])

    def test_negated_mentions_are_not_claims(self):
        for t in ["No supplement can guarantee a result, so please check with your clinician.",
                  "I cannot guarantee that this will work.", "This is not a cure and nobody should promise one.",
                  "Nothing here is guaranteed; the clinic will confirm."]:
            self.assertTrue(output_guard(t)["ok"], t)

    def test_a_blocked_reply_records_the_phrase_that_tripped_the_rule(self):
        r = output_guard("Honestly this protocol is guaranteed to work for you.")
        self.assertFalse(r["ok"])
        self.assertIn("guaranteed", r["excerpts"]["guarantee"])

    def test_non_string_input_returns_a_result_instead_of_raising(self):
        for x in (None, ["a"], {"x": 1}, 42):
            r = output_guard(x)
            self.assertIsInstance(r["text"], str, x)
            self.assertIn("ok", r)
        self.assertEqual(output_guard(None)["text"], "")

    def test_a_blocked_phrase_inside_a_non_string_still_blocks(self):
        r = output_guard(["Take 500 mg daily"])
        self.assertFalse(r["ok"])
        self.assertIn("dose", r["violations"])
        self.assertEqual(r["text"], SAFE_REPLACEMENT)

    def test_plain_explanations_and_referrals_pass(self):
        for t in ["LDL of 4.1 mmol/L is above the reference range the lab printed; a clinician can tell you what it means.",
                  "Your ferritin is lower than the printed range. Please book a visit with your doctor.",
                  "I can't give a dose. Ask your pharmacist."]:
            r = output_guard(t)
            self.assertTrue(r["ok"], (t, r))
            self.assertEqual(r["text"], t)


if __name__ == "__main__":
    unittest.main()
