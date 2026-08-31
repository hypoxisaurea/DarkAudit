import unittest

from ai.schemas.audit_schema import LLMAuditOutput


VALID = {
    "screen_id": "screen_03", "flow_step": "부가서비스",
    "detections": [{
        "risk_type": "PRESELECTED_OPTION", "risk_name": "특정옵션의 사전선택",
        "where": {"element": "자동결제 동의 checkbox", "location": "화면 중앙"},
        "what": "사용자 입력 전에 체크되어 있음", "observation": "checked 상태가 true임",
        "rule_id": "DA-04", "why": "명시적 선택 없이 옵션 수용을 유도할 수 있음",
        "severity": "HIGH", "confidence": 0.91, "fix": "기본값을 미선택으로 변경"
    }]
}


class AuditSchemaTest(unittest.TestCase):
    def test_valid_contract(self):
        self.assertEqual(LLMAuditOutput.from_dict(VALID).detections[0].rule_id, "DA-04")

    def test_rejects_wrong_rule_mapping(self):
        detection = {**VALID["detections"][0], "rule_id": "DA-03"}
        with self.assertRaises(ValueError):
            LLMAuditOutput.from_dict({**VALID, "detections": [detection]})

    def test_rejects_high_standalone_emotional_language(self):
        detection = {**VALID["detections"][0], "risk_type": "EMOTIONAL_LANGUAGE",
                     "risk_name": "감정적 언어", "rule_id": "DA-12"}
        with self.assertRaises(ValueError):
            LLMAuditOutput.from_dict({**VALID, "detections": [detection]})


if __name__ == "__main__":
    unittest.main()
