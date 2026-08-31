import tempfile
import unittest
from pathlib import Path
from ai.pipeline.baseline import BaselineAuditPipeline
from ai.schemas.audit_schema import AuditScreen, LLMAuditOutput, LLMAuditRequest

def output(detections=None):
    return {"audit_id": "audit_1", "schema_version": "1.0",
            "screens": [{"screen_id": "screen_01", "flow_step": "부가서비스"}],
            "detections": detections or []}

class FakeProvider:
    def __init__(self, result): self.result, self.rules = result, None
    def analyze(self, request, system_prompt, audit_prompt, rules, output_schema):
        self.rules = rules
        return self.result

class AuditSchemaTest(unittest.TestCase):
    def test_valid_empty_contract(self):
        self.assertEqual(LLMAuditOutput.from_dict(output()).detections, ())

    def test_rejects_high_standalone_emotional_language(self):
        detection = {"risk_type": "EMOTIONAL_LANGUAGE", "risk_name": "감정적 언어",
                     "where": {"screen_ids": ["screen_01"], "element": "거절 버튼", "location": "하단"},
                     "what": "감정 표현", "observation": "혜택을 포기", "rule_id": "DA-12",
                     "why": "손실을 자극", "severity": "HIGH", "confidence": .9, "fix": "중립화"}
        with self.assertRaises(ValueError): LLMAuditOutput.from_dict(output([detection]))

    def test_baseline_passes_only_mvp_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "screen.png"
            image.write_bytes(b"png")
            request = LLMAuditRequest("audit_1", (AuditScreen("screen_01", "부가서비스", image),))
            provider = FakeProvider(output())
            result = BaselineAuditPipeline(provider).analyze(request)
            self.assertEqual(result.audit_id, "audit_1")
            self.assertEqual({rule["rule_id"] for rule in provider.rules}, {"DA-03", "DA-04", "DA-12", "DA-15"})

if __name__ == "__main__": unittest.main()
