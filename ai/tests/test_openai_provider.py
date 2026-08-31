import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ai.providers.openai_provider import OpenAIResponsesProvider
from ai.schemas.audit_schema import AuditScreen, LLMAuditRequest


class FakeResponses:
    def __init__(self): self.kwargs = None
    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(output_text='{"ok": true}')


class OpenAIProviderTest(unittest.TestCase):
    def test_builds_responses_api_image_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "screen.png"
            image.write_bytes(b"png")
            responses = FakeResponses()
            client = SimpleNamespace(responses=responses)
            request = LLMAuditRequest("audit", (AuditScreen("screen_01", "가입", image),))
            result = OpenAIResponsesProvider("test-model", client).analyze(request, "system", "audit", [], {"type": "object"})
            self.assertEqual(result, {"ok": True})
            self.assertEqual(responses.kwargs["model"], "test-model")
            content = responses.kwargs["input"][0]["content"]
            self.assertTrue(any(item["type"] == "input_image" and item["image_url"].startswith("data:image/png;base64,") for item in content))
            self.assertTrue(responses.kwargs["text"]["format"]["strict"])


if __name__ == "__main__": unittest.main()
