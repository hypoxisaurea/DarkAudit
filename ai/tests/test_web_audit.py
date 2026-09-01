import unittest
from pathlib import Path

from ai.browser.models import CaptureArtifact
from ai.pipeline.web_audit import select_analysis_artifacts


def artifact(index: int) -> CaptureArtifact:
    return CaptureArtifact(
        f"screen_{index}", f"step {index}", "desktop", "https://example.com", "Example",
        Path(f"screen-{index}.png"), 1440, 900, fingerprint=f"hash-{index}",
    )


class WebAuditSelectionTest(unittest.TestCase):
    def test_evenly_selects_first_middle_and_last_states(self):
        selected = select_analysis_artifacts(tuple(artifact(index) for index in range(9)), 5)
        self.assertEqual([item.screen_id for item in selected], [
            "screen_0", "screen_2", "screen_4", "screen_6", "screen_8",
        ])


if __name__ == "__main__":
    unittest.main()
