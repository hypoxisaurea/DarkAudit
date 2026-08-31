"""Strict request/response contract for the multimodal MVP baseline."""
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any

class RiskType(str, Enum):
    PRESELECTED_OPTION = "PRESELECTED_OPTION"
    VISUAL_HIERARCHY_DISTORTION = "VISUAL_HIERARCHY_DISTORTION"
    EMOTIONAL_LANGUAGE = "EMOTIONAL_LANGUAGE"
    SEQUENTIAL_PRICE_DISCLOSURE = "SEQUENTIAL_PRICE_DISCLOSURE"

class Severity(str, Enum):
    REVIEW = "REVIEW"
    HIGH = "HIGH"

RISK_RULE_MAP = {RiskType.PRESELECTED_OPTION: "DA-04", RiskType.VISUAL_HIERARCHY_DISTORTION: "DA-03",
                 RiskType.EMOTIONAL_LANGUAGE: "DA-12", RiskType.SEQUENTIAL_PRICE_DISCLOSURE: "DA-15"}
RISK_NAME_MAP = {RiskType.PRESELECTED_OPTION: "특정옵션의 사전선택", RiskType.VISUAL_HIERARCHY_DISTORTION: "잘못된 계층구조",
                 RiskType.EMOTIONAL_LANGUAGE: "감정적 언어", RiskType.SEQUENTIAL_PRICE_DISCLOSURE: "순차공개 가격책정"}

@dataclass(frozen=True, slots=True)
class AuditScreen:
    screen_id: str
    flow_step: str
    image_path: Path
    def __post_init__(self) -> None:
        object.__setattr__(self, "image_path", Path(self.image_path))
        if not self.screen_id.strip() or not self.flow_step.strip(): raise ValueError("screen_id and flow_step are required")
        if not self.image_path.is_file(): raise FileNotFoundError(self.image_path)

@dataclass(frozen=True, slots=True)
class LLMAuditRequest:
    audit_id: str
    screens: tuple[AuditScreen, ...]
    schema_version: str = "1.0"
    def __post_init__(self) -> None:
        if not self.audit_id.strip() or not 1 <= len(self.screens) <= 5: raise ValueError("audit_id and 1 to 5 screens are required")
        ids = [screen.screen_id for screen in self.screens]
        if len(ids) != len(set(ids)): raise ValueError("screen_id values must be unique")

@dataclass(frozen=True, slots=True)
class ScreenReference:
    screen_id: str
    flow_step: str

@dataclass(frozen=True, slots=True)
class DetectionLocation:
    screen_ids: tuple[str, ...]
    element: str
    location: str
    def __post_init__(self) -> None:
        if not self.screen_ids or not self.element.strip() or not self.location.strip(): raise ValueError("where fields are required")

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
        if not 0 <= self.confidence <= 1: raise ValueError("confidence must be between 0 and 1")
        if self.rule_id != RISK_RULE_MAP[self.risk_type] or self.risk_name != RISK_NAME_MAP[self.risk_type]: raise ValueError("invalid risk mapping")
        if self.risk_type is RiskType.EMOTIONAL_LANGUAGE and self.severity is Severity.HIGH: raise ValueError("DA-12 is REVIEW-only in v1")
        if self.risk_type is RiskType.SEQUENTIAL_PRICE_DISCLOSURE and len(self.where.screen_ids) < 2: raise ValueError("DA-15 requires two screens")
        if any(not getattr(self, name).strip() for name in ("what", "observation", "why", "fix")): raise ValueError("narrative fields are required")
    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Detection":
        fields = {"risk_type", "risk_name", "where", "what", "observation", "rule_id", "why", "severity", "confidence", "fix"}
        if set(value) != fields or set(value["where"]) != {"screen_ids", "element", "location"}: raise ValueError("invalid detection fields")
        where = value["where"]
        return cls(RiskType(value["risk_type"]), value["risk_name"], DetectionLocation(tuple(where["screen_ids"]), where["element"], where["location"]), value["what"], value["observation"], value["rule_id"], value["why"], Severity(value["severity"]), float(value["confidence"]), value["fix"])

@dataclass(frozen=True, slots=True)
class LLMAuditOutput:
    audit_id: str
    schema_version: str
    screens: tuple[ScreenReference, ...]
    detections: tuple[Detection, ...]
    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "LLMAuditOutput":
        if set(value) != {"audit_id", "schema_version", "screens", "detections"}: raise ValueError("invalid output fields")
        screens = tuple(ScreenReference(**screen) for screen in value["screens"])
        output = cls(value["audit_id"], value["schema_version"], screens, tuple(Detection.from_dict(item) for item in value["detections"]))
        valid_ids = {screen.screen_id for screen in screens}
        if any(sid not in valid_ids for finding in output.detections for sid in finding.where.screen_ids): raise ValueError("unknown screen_id reference")
        return output
    def to_dict(self) -> dict[str, Any]: return asdict(self)
