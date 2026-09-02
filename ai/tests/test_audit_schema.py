import copy
import tempfile
import unittest
from pathlib import Path

from ai.evaluation import Evaluator
from ai.pipeline.baseline import BaselineAuditPipeline
from ai.schemas.audit_schema import AuditScreen, LLMAuditOutput, LLMAuditRequest, SCHEMA_VERSION


GOLDEN_PATH = Path(__file__).with_name("golden_cases.jsonl")


def output(detections=None, screens=None):
    return {
        "audit_id": "audit_1",
        "schema_version": SCHEMA_VERSION,
        "screens": screens or [{"screen_id": "screen_01", "flow_step": "desktop: 부가서비스"}],
        "detections": detections or [],
    }


def detection(
    risk_type="EMOTIONAL_LANGUAGE",
    risk_name="감정적 언어",
    rule_id="DA-12",
    severity="REVIEW",
    screen_ids=None,
    bbox=None,
    related_elements=None,
):
    return {
        "risk_type": risk_type,
        "risk_name": risk_name,
        "where": {
            "screen_ids": screen_ids or ["screen_01"],
            "element": "혜택을 포기할래요 버튼",
            "location": "화면 하단",
        },
        "bbox": bbox or [0.08, 0.72, 0.84, 0.10],
        "related_elements": related_elements or [],
        "what": "감정적 거절 문구",
        "observation": "거절 버튼에 혜택 포기라는 문구가 표시됨",
        "rule_id": rule_id,
        "why": "거절에 손실 프레이밍을 사용함",
        "severity": severity,
        "confidence": 0.9,
        "fix": "거절 문구를 중립적으로 바꾼다.",
    }


def da15(screen_ids):
    return detection(
        risk_type="SEQUENTIAL_PRICE_DISCLOSURE",
        risk_name="순차공개 가격책정",
        rule_id="DA-15",
        severity="HIGH",
        screen_ids=screen_ids,
        bbox=[0.10, 0.20, 0.40, 0.08],
        related_elements=[{
            "screen_id": screen_ids[0],
            "element": "최초 표시 가격",
            "bbox": [0.10, 0.20, 0.40, 0.08],
        }],
    )


class FakeProvider:
    def __init__(self, result):
        self.result, self.rules = result, None

    def analyze(self, request, system_prompt, audit_prompt, rules, output_schema):
        self.rules = rules
        return self.result


class AuditSchemaTest(unittest.TestCase):
    def test_valid_empty_contract(self):
        self.assertEqual(LLMAuditOutput.from_dict(output()).detections, ())

    def test_severity_is_rule_base_base_severity(self):
        invalid_da12 = detection(severity="HIGH")
        invalid_da03 = detection(
            risk_type="VISUAL_HIERARCHY_DISTORTION",
            risk_name="잘못된 계층구조",
            rule_id="DA-03",
            severity="REVIEW",
            related_elements=[{
                "screen_id": "screen_01",
                "element": "다음에 하기 버튼",
                "bbox": [0.08, 0.86, 0.84, 0.06],
            }],
        )
        for item in (invalid_da12, invalid_da03):
            with self.subTest(rule_id=item["rule_id"]), self.assertRaises(ValueError):
                LLMAuditOutput.from_dict(output([item]))

    def test_rejects_bbox_outside_normalized_screen(self):
        item = detection(bbox=[0.8, 0.2, 0.3, 0.1])
        with self.assertRaisesRegex(ValueError, "inside the screen"):
            LLMAuditOutput.from_dict(output([item]))

    def test_da03_requires_distinct_related_element_pair(self):
        item = detection(
            risk_type="VISUAL_HIERARCHY_DISTORTION",
            risk_name="잘못된 계층구조",
            rule_id="DA-03",
            severity="HIGH",
        )
        with self.assertRaisesRegex(ValueError, "counterpart"):
            LLMAuditOutput.from_dict(output([item]))

    def test_golden_allows_multiple_rule_labels_on_same_element(self):
        golden = Evaluator.load_golden(GOLDEN_PATH)
        case = next(item for item in golden if item["case_id"] == "multi-label-same-element")
        parsed = LLMAuditOutput.from_dict(case["expected_output"])

        self.assertEqual(
            {item.rule_id for item in parsed.detections},
            set(case["expected_rule_ids"]),
        )
        self.assertEqual(len({item.bbox for item in parsed.detections}), 1)
        da03_finding = next(item for item in parsed.detections if item.rule_id == "DA-03")
        self.assertGreaterEqual(len(da03_finding.related_elements), 1)

    def test_da15_accepts_only_same_device_profile(self):
        same_profile_screens = [
            {"screen_id": "screen_01", "flow_step": "mobile: 상품 목록"},
            {"screen_id": "screen_02", "flow_step": "mobile: 최종 확인"},
        ]
        parsed = LLMAuditOutput.from_dict(output([da15(["screen_01", "screen_02"])], same_profile_screens))
        self.assertEqual(parsed.detections[0].rule_id, "DA-15")

        cross_profile_screens = copy.deepcopy(same_profile_screens)
        cross_profile_screens[1]["flow_step"] = "desktop: 최종 확인"
        with self.assertRaisesRegex(ValueError, "same device profile"):
            LLMAuditOutput.from_dict(output([da15(["screen_01", "screen_02"])], cross_profile_screens))

    def test_baseline_passes_only_mvp_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "screen.png"
            image.write_bytes(b"png")
            request = LLMAuditRequest("audit_1", (AuditScreen("screen_01", "desktop: 부가서비스", image),))
            provider = FakeProvider(output())
            result = BaselineAuditPipeline(provider).analyze(request)
            self.assertEqual(result.audit_id, "audit_1")
            self.assertEqual({rule["rule_id"] for rule in provider.rules}, {"DA-03", "DA-04", "DA-12", "DA-15"})


if __name__ == "__main__":
    unittest.main()
