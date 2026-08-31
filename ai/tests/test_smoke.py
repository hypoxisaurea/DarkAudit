from ai.pipeline.analyzer import AuditAnalyzer
from ai.schemas.audit_input import AuditInput, ScreenInput


def test_analyzer_accepts_text_only_screen():
    result = AuditAnalyzer().analyze(AuditInput("smoke", [ScreenInput("screen-1", text="상품 안내")]))
    assert result.audit_id == "smoke"
    assert result.findings == []
