import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ai.browser.models import BrowserActionType
from ai.providers.computer_use import OpenAIComputerUseAgent


class FakeResponses:
    def __init__(self): self.calls = []
    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            action = SimpleNamespace(type="screenshot")
            call = SimpleNamespace(
                type="computer_call", call_id="call-1", actions=[action],
                pending_safety_checks=[],
            )
            return SimpleNamespace(id="response-1", output=[call], output_text="")
        return SimpleNamespace(id="response-2", output=[], output_text="done")


class ComputerUseProviderTest(unittest.TestCase):
    def test_runs_responses_api_screenshot_loop(self):
        with tempfile.TemporaryDirectory() as directory:
            screenshot = Path(directory) / "screen.png"
            screenshot.write_bytes(b"png")
            responses = FakeResponses()
            agent = OpenAIComputerUseAgent("test-model", SimpleNamespace(responses=responses))

            first = agent.begin("inspect pricing")
            final = agent.resume(first, screenshot)

            self.assertEqual(first.actions[0].type, BrowserActionType.SCREENSHOT)
            self.assertTrue(final.is_finished)
            self.assertEqual(responses.calls[0]["tools"], [{"type": "computer"}])
            second = responses.calls[1]
            self.assertEqual(second["previous_response_id"], "response-1")
            output = second["input"][0]["output"]
            self.assertEqual(output["type"], "computer_screenshot")
            self.assertEqual(output["detail"], "original")
            self.assertTrue(output["image_url"].startswith("data:image/png;base64,"))


if __name__ == "__main__":
    unittest.main()
