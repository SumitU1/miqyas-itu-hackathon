import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.audit import AuditLog, sha256_text  # noqa: E402
from agents.llm import ModelClient, extract_json, load_key  # noqa: E402

SECRET = "sk-test-SECRET-0123456789"


def ok_reply(content, model="moonshotai/kimi-k2"):
    return 200, {"model": model, "choices": [{"message": {"content": content}, "finish_reason": "stop"}]}


class LLMTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "run.jsonl"
        self.audit = AuditLog(self.path, "t")
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def client(self, replies):
        replies = list(replies)

        def transport(url, headers, body, timeout):
            self.calls.append((url, headers, body))
            return replies.pop(0)

        return ModelClient("http://127.0.0.1:3001/v1", SECRET, self.audit, transport=transport, retries=1, backoff=0)

    def records(self):
        return [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines()]

    def test_request_uses_the_auto_alias_and_a_bearer_key(self):
        c = self.client([ok_reply("hello")])
        r = c.complete("agent:coach", "SYS", "USER")
        url, headers, body = self.calls[0]
        self.assertTrue(url.endswith("/chat/completions"))
        self.assertEqual(body["model"], "auto")
        self.assertEqual(headers["Authorization"], f"Bearer {SECRET}")
        self.assertEqual(r["text"], "hello")
        self.assertTrue(r["ok"])

    def test_audit_records_alias_served_model_and_prompt_hash_but_never_the_key_or_prompt_text(self):
        c = self.client([ok_reply("hi")])
        c.complete("agent:coach", "SYS-PROMPT", "USER-PROMPT")
        rec = self.records()[-1]
        self.assertEqual(rec["type"], "model_call")
        self.assertEqual(rec["payload"]["model_alias"], "auto")
        self.assertEqual(rec["payload"]["served_model"], "moonshotai/kimi-k2")
        self.assertEqual(rec["payload"]["prompt_hash"], sha256_text("SYS-PROMPT\n---\nUSER-PROMPT"))
        raw = self.path.read_text(encoding="utf-8")
        self.assertNotIn(SECRET, raw)
        self.assertNotIn("USER-PROMPT", raw)

    def test_a_502_is_retried_once_then_succeeds(self):
        c = self.client([(502, "bad gateway"), ok_reply("second try")])
        r = c.complete("a", "s", "u")
        self.assertTrue(r["ok"])
        self.assertEqual(r["text"], "second try")
        self.assertEqual(len(self.calls), 2)

    def test_persistent_failure_returns_not_ok_and_logs_the_error_without_the_key(self):
        c = self.client([(502, f"upstream said {SECRET}"), (502, "x")])
        r = c.complete("a", "s", "u")
        self.assertFalse(r["ok"])
        self.assertNotIn(SECRET, json.dumps(r))
        self.assertNotIn(SECRET, self.path.read_text(encoding="utf-8"))
        self.assertFalse(self.records()[-1]["payload"]["ok"])

    def test_empty_content_counts_as_failure(self):
        c = self.client([ok_reply(""), ok_reply("")])
        self.assertFalse(c.complete("a", "s", "u")["ok"])

    def test_non_string_content_counts_as_an_empty_reply_not_a_crash(self):
        for content in (["a", "b"], 5, {"text": "hi"}, True):
            c = self.client([ok_reply(content), ok_reply(content)])
            r = c.complete("a", "s", "u")
            self.assertFalse(r["ok"], content)
            self.assertEqual(r["error"], "empty reply", content)
        c = self.client([ok_reply(["a"]), ok_reply("fine")])
        self.assertEqual(c.complete("a", "s", "u")["text"], "fine")

    def test_gateway_unreachable_is_a_failure_not_a_crash(self):
        def boom(*a):
            raise OSError("connection refused")
        c = ModelClient("http://x/v1", SECRET, self.audit, transport=boom, retries=0, backoff=0)
        r = c.complete("a", "s", "u")
        self.assertFalse(r["ok"])
        self.assertIn("connection refused", r["error"])


class ExtractJson(unittest.TestCase):
    def test_plain_fenced_prose_wrapped_and_think_tagged(self):
        self.assertEqual(extract_json('{"a": 1}'), {"a": 1})
        self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(extract_json('Here you go:\n{"a": {"b": [1,2]}}\nThanks'), {"a": {"b": [1, 2]}})
        self.assertEqual(extract_json('<think>{"x":0} hmm</think>{"a": 2}'), {"a": 2})

    def test_garbage_returns_none(self):
        self.assertIsNone(extract_json("no json here"))
        self.assertIsNone(extract_json('{"a": '))


class AsList(unittest.TestCase):
    def test_lists_strings_and_junk(self):
        from agents.llm import as_list
        self.assertEqual(as_list(["a", "b"]), ["a", "b"])
        self.assertEqual(as_list("a"), ["a"])
        self.assertEqual(as_list("a, b;c"), ["a, b;c"])
        self.assertEqual(as_list("a, b;c", split=True), ["a", "b", "c"])
        self.assertEqual(as_list(None), [])
        self.assertEqual(as_list(""), [])
        self.assertEqual(as_list({"x": 1}), [])
        self.assertEqual(as_list(7), ["7"])


class LoadKey(unittest.TestCase):
    def test_env_var_wins_then_env_file_and_the_error_never_contains_a_key(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / ".env"
            f.write_text("OTHER=1\nGATEWAY_LLM_KEY=" + SECRET + "\n", encoding="utf-8")
            self.assertEqual(load_key({"GATEWAY_LLM_KEY": "from-env"}), "from-env")
            self.assertEqual(load_key({"GATEWAY_ENV_FILE": str(f)}), SECRET)
            with self.assertRaises(RuntimeError) as cm:
                load_key({})
            self.assertNotIn(SECRET, str(cm.exception))


if __name__ == "__main__":
    unittest.main()
