"""Offline tests only; never charge live APIs from a test run."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("api_delegate", Path(__file__).resolve().parents[1] / "tools/api_delegate.py")
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


class APIBoundaries(unittest.TestCase):
    def test_model_context_suffix(self):
        self.assertEqual(api.normalize_model("deepseek-v4-pro[1M]"), "deepseek-v4-pro")

    def test_protocol_and_bounded_payload(self):
        for protocol in ("anthropic", "responses"):
            provider = {"base_url": "https://example.invalid/api", "key": "fake-test-secret", "model": "test", "protocol": protocol}
            endpoint, _, payload = api.build_request(provider, "public task", 128)
            self.assertTrue(endpoint.startswith("https://example.invalid/"))
            self.assertFalse(payload["stream"])
            self.assertEqual(payload["thinking"], {"type": "disabled"})
            self.assertNotIn("tools", payload)
            self.assertNotIn("fake-test-secret", json.dumps(payload))
            with self.assertRaises(ValueError):
                api.build_request(provider, "public task", 1501)

    def test_response_extractors_exclude_thinking(self):
        self.assertEqual(api.response_text({"content": [{"type": "thinking", "thinking": "hidden"}, {"type": "text", "text": "ok"}]}, "anthropic"), "ok")
        self.assertEqual(api.response_text({"output": [{"type": "reasoning", "content": []}, {"type": "message", "content": [{"type": "output_text", "text": "ok"}]}]}, "responses"), "ok")

    def test_usage_allowlist(self):
        self.assertEqual(api.usage_only({"usage": {"input_tokens": 10, "secret": "fake", "output_tokens_details": {"reasoning_tokens": 0, "bad": "fake"}}}), {"input_tokens": 10, "output_tokens_details": {"reasoning_tokens": 0}})

    def test_success_prevents_repeat_but_failure_does_not(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "calls.jsonl"
            path.write_text(json.dumps({"alias": "grok", "task": "t", "status": "http_error"}) + "\n", encoding="utf-8")
            self.assertFalse(api.already_succeeded(path, "grok", "t"))
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"alias": "grok", "task": "t", "status": "success"}) + "\n")
            self.assertTrue(api.already_succeeded(path, "grok", "t"))

    def test_credentials_never_follow_redirects(self):
        self.assertIsNone(api.NoRedirect().redirect_request(None, None, 302, "moved", {}, "https://example.invalid/other"))


if __name__ == "__main__":
    unittest.main()
