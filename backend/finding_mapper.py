"""Translate the internal AI contract to the frontend DTO contract."""
import uuid
from typing import Any
from ai.schemas.audit_schema import Detection
from backend.schemas import FindingDto

def to_finding_dto(detection: Detection, rules: dict[str, dict[str, Any]]) -> FindingDto:
    rule = rules[detection.rule_id]
    return FindingDto(
        id=f"finding-{uuid.uuid4().hex}", ruleId=detection.rule_id,
        riskType=detection.risk_type.value, title=detection.risk_name,
        description=f"{detection.what} {detection.why}", screenIds=list(detection.where.screen_ids),
        element=detection.where.element, severity=detection.severity.value, status="open",
        confidence=detection.confidence, recommendation=detection.fix,
        guideline=rule["official_definition"],
    )
