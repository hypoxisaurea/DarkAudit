"""Strict contract for multimodal LLM audit responses (schema version 1.0)."""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class RiskType(str, Enum):
    PRESELECTED_OPTION = "PRESELECTED_OPTION"
    VISUAL_HIERARCHY_DISTORTION = "VISUAL_HIERARCHY_DISTORTION"
    EMOTIONAL_LANGUAGE = "EMOTIONAL_LANGUAGE"
    SEQUENTIAL_PRICE_DISCLOSURE = "SEQUENTIAL_PRICE_DISCLOSURE"


class Severity(str, Enum):
    REVIEW = "REVIEW"
    HIGH = "HIGH"


RISK_RULE_MAP = {
    RiskType.PRESELECTED_OPTION: "DA-04",
    RiskType.VISUAL_HIERARCHY_DISTORTION: "DA-03",
    RiskType.EMOTIONAL_LANGUAGE: "DA-12",
    RiskType.SEQUENTIAL_PRICE_DISCLOSURE: "DA-15",
}
RISK_NAME_MAP = {
    RiskType.PRESELECTED_OPTION: "특정옵션의 사전선택",
    RiskType.VISUAL_HIERARCHY_DISTORTION: "잘못된 계층구조",
    RiskType.EMOTIONAL_LANGUAGE: "감정적 언어",
    RiskType.SEQUENTIAL_PRICE_DISCLOSURE: "순차공개 가격책정",
}


@dataclass(frozen=True, slots=True)
class DetectionLocation:
    element: str
    location: str

    def __post_init__(self) -> None:
        if not self.element.strip() or not self.location.strip():
            raise ValueError("where fields must not be empty")


@dataclass(frozen=True, slots=True)
class Detection:
    risk_type: RiskType
    risk_name: str
    where: DetectionLocation
    what: str
    observation: str
    rule_id: str
    why: str
    severity: Severity
    confidence: float
    fix: str

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if self.rule_id != RISK_RULE_MAP[self.risk_type] or self.risk_name != RISK_NAME_MAP[self.risk_type]:
            raise ValueError("risk_type, risk_name and rule_id mapping is invalid")
        if self.risk_type is RiskType.EMOTIONAL_LANGUAGE and self.severity is Severity.HIGH:
            raise ValueError("DA-12 is REVIEW-only without combination evidence in v1")
        if any(not getattr(self, field).strip() for field in ("what", "observation", "why", "fix")):
            raise ValueError("Narrative fields must not be empty")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Detection":
        fields = {"risk_type", "risk_name", "where", "what", "observation", "rule_id", "why", "severity", "confidence", "fix"}
        if set(value) != fields:
            raise ValueError(f"Detection fields must be exactly {sorted(fields)}")
        return cls(RiskType(value["risk_type"]), value["risk_name"], DetectionLocation(**value["where"]),
                   value["what"], value["observation"], value["rule_id"], value["why"],
                   Severity(value["severity"]), float(value["confidence"]), value["fix"])


@dataclass(frozen=True, slots=True)
class LLMAuditOutput:
    screen_id: str
    flow_step: str
    detections: tuple[Detection, ...]

    def __post_init__(self) -> None:
        if not self.screen_id.strip() or not self.flow_step.strip():
            raise ValueError("screen_id and flow_step must not be empty")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "LLMAuditOutput":
        if set(value) != {"screen_id", "flow_step", "detections"}:
            raise ValueError("Output fields must be exactly screen_id, flow_step and detections")
        return cls(value["screen_id"], value["flow_step"], tuple(Detection.from_dict(item) for item in value["detections"]))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
