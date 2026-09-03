import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ai.providers.openai_provider import OpenAIResponsesProvider, _responses_schema
from ai.schemas.audit_schema import AuditScreen, LLMAuditRequest


class FakeResponses:
    def __init__(self): self.kwargs = None
    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(output_text='{"ok": true}')


class OpenAIProviderTest(unittest.TestCase):
    def test_removes_unsupported_conditional_schema_keywords(self):
        schema = {
            "type": "object",
            "properties": {"kind": {"type": "string"}},
            "allOf": [{"if": {"properties": {}}, "then": {"required": ["kind"]}}],
        }
        normalized = _responses_schema(schema)
        self.assertNotIn("allOf", normalized)
        self.assertEqual(normalized["properties"], schema["properties"])

    def test_adds_type_to_const_only_schema(self):
        self.assertEqual(
            _responses_schema({"const": "1.1"}),
            {"const": "1.1", "type": "string"},
        )

    def test_builds_responses_api_image_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "screen.png"
            image.write_bytes(b"png")
            responses = FakeResponses()
            client = SimpleNamespace(responses=responses)
            request = LLMAuditRequest("audit", (AuditScreen("screen_01", "가입", image),))
            result = OpenAIResponsesProvider("test-model", client).analyze(
                request, "system", "audit", [], {"type": "object"},
                [{"rule_id": "DA-04", "measurements": {"checked": True}}],
            )
            self.assertEqual(result, {"ok": True})
            self.assertEqual(responses.kwargs["model"], "test-model")
            content = responses.kwargs["input"][0]["content"]
            self.assertTrue(any(item["type"] == "input_image" and item["image_url"].startswith("data:image/png;base64,") for item in content))
            self.assertTrue(any("audit_id=audit" in item.get("text", "") for item in content))
            self.assertTrue(any('"checked": true' in item.get("text", "") for item in content))
            candidate_text = next(
                item["text"] for item in content
                if item.get("text", "").startswith("Deterministic Candidates")
            )
            self.assertIn("exactly one KEEP or REJECT", candidate_text)
            self.assertIn("Never copy a candidate into semantic_findings", candidate_text)
            self.assertIn("semantic-only checks", candidate_text)
            self.assertIn("Do not calculate final severity", candidate_text)
            self.assertTrue(responses.kwargs["text"]["format"]["strict"])


if __name__ == "__main__": unittest.main()
