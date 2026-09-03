import json
import tempfile
import unittest
from pathlib import Path

from ai.evaluation import DatasetCase, Evaluator


def detection(rule_id="DA-04", bbox=None):
    return {
        "rule_id": rule_id,
        "bbox": bbox or [0.1, 0.2, 0.2, 0.1],
        "where": {"screen_ids": ["screen_01"]},
    }


class DatasetEvaluationTest(unittest.TestCase):
    def test_loads_real_label_dataset(self):
        cases = Evaluator.load_dataset(Path("data/synthetic/labels"))
        self.assertEqual(len(cases), 22)
        self.assertEqual(len({case.pair_id for case in cases}), 11)
        self.assertTrue(any(case.labels for case in cases))

    def test_reports_quality_localization_counterfactual_and_operations(self):
        cases = [
            DatasetCase("pair-clean", "pair", "clean", ({"screen_index": 1},), ()),
            DatasetCase("pair-risky", "pair", "risky", ({"screen_index": 1},), ({
                "rule_id": "DA-04", "primary": {"screen_index": 1, "bbox": [0.1, 0.2, 0.2, 0.1]},
            },)),
        ]
        predictions = {
            "pair-clean": {"output": {"detections": []}, "telemetry": {
                "response_time_seconds": 1, "screen_count": 1, "url_exploration_success": True,
                "schema_attempts": 1, "schema_retries": 0,
                "usage": {"input_tokens": 1000, "output_tokens": 100},
            }},
            "pair-risky": {"output": {"detections": [detection()]}, "telemetry": {
                "response_time_seconds": 3, "screen_count": 1, "url_exploration_success": False,
                "schema_attempts": 2, "schema_retries": 1,
                "usage": {"input_tokens": 1000, "output_tokens": 100},
            }},
        }
        report = Evaluator().evaluate_dataset(
            cases, predictions, input_usd_per_million=1, output_usd_per_million=2
        )
        self.assertEqual(report["micro"]["f1"], 1.0)
        self.assertEqual(report["macro"]["f1"], 1.0)
        self.assertEqual(report["counterfactual_consistency"]["score"], 1.0)
        self.assertEqual(report["localization"]["success_rate"], 1.0)
        self.assertEqual(report["operations"]["url_exploration_success_rate"], 0.5)
        self.assertEqual(report["operations"]["average_response_time_seconds"], 2.0)
        self.assertAlmostEqual(report["operations"]["model_cost_usd_per_screen"], 0.0012)
        self.assertAlmostEqual(report["operations"]["schema_retry_rate"], 1 / 3)

    def test_loads_prediction_envelope(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "case.json"
            path.write_text(json.dumps({"flow_id": "flow", "output": {"detections": []},
                                        "telemetry": {"schema_attempts": 1}}), encoding="utf-8")
            loaded = Evaluator.load_predictions(directory)
            self.assertEqual(loaded["flow"]["telemetry"]["schema_attempts"], 1)


if __name__ == "__main__":
    unittest.main()
