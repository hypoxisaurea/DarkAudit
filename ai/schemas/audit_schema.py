"""Strict request/response contract for the multimodal MVP baseline."""

from dataclasses import asdict, dataclass
from enum import Enum
import math
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.1"
DEVICE_PROFILES = frozenset({"desktop", "mobile", "iphone"})


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

# ``severity`` is the Rule Base severity before downstream combination or
# mitigation scoring. It is intentionally not the final severity.
BASE_SEVERITY_MAP = {
    RiskType.PRESELECTED_OPTION: Severity.HIGH,
    RiskType.VISUAL_HIERARCHY_DISTORTION: Severity.HIGH,
    RiskType.EMOTIONAL_LANGUAGE: Severity.REVIEW,
    RiskType.SEQUENTIAL_PRICE_DISCLOSURE: Severity.HIGH,
}

NormalizedBBox = tuple[float, float, float, float]


def _normalized_bbox(value: Any, field_name: str = "bbox") -> NormalizedBBox:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError(f"{field_name} must be [x, y, width, height]")
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
        raise ValueError(f"{field_name} values must be numbers")
    bbox = tuple(float(item) for item in value)
    if any(not math.isfinite(item) or not 0 <= item <= 1 for item in bbox):
        raise ValueError(f"{field_name} values must be finite and between 0 and 1")
    x, y, width, height = bbox
    if width <= 0 or height <= 0 or x + width > 1 + 1e-9 or y + height > 1 + 1e-9:
        raise ValueError(f"{field_name} must be a positive rectangle inside the screen")
    return bbox  # type: ignore[return-value]


def _device_profile(flow_step: str) -> str:
    prefix, separator, _ = flow_step.partition(":")
    candidate = prefix.strip().lower()
    return candidate if separator and candidate in DEVICE_PROFILES else "unspecified"


@dataclass(frozen=True, slots=True)
class AuditScreen:
    screen_id: str
    flow_step: str
    image_path: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "image_path", Path(self.image_path))
        if not self.screen_id.strip() or not self.flow_step.strip():
            raise ValueError("screen_id and flow_step are required")
        if not self.image_path.is_file():
            raise FileNotFoundError(self.image_path)


@dataclass(frozen=True, slots=True)
class LLMAuditRequest:
    audit_id: str
    screens: tuple[AuditScreen, ...]
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.audit_id.strip() or not 1 <= len(self.screens) <= 5:
            raise ValueError("audit_id and 1 to 5 screens are required")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
        ids = [screen.screen_id for screen in self.screens]
        if len(ids) != len(set(ids)):
            raise ValueError("screen_id values must be unique")


@dataclass(frozen=True, slots=True)
class ScreenReference:
    screen_id: str
    flow_step: str

    def __post_init__(self) -> None:
        if not self.screen_id.strip() or not self.flow_step.strip():
            raise ValueError("screen reference fields are required")

    @property
    def device_profile(self) -> str:
        return _device_profile(self.flow_step)


@dataclass(frozen=True, slots=True)
class DetectionLocation:
    screen_ids: tuple[str, ...]
    element: str
    location: str

    def __post_init__(self) -> None:
        if not self.screen_ids or not self.element.strip() or not self.location.strip():
            raise ValueError("where fields are required")
        if len(self.screen_ids) != len(set(self.screen_ids)):
            raise ValueError("where.screen_ids must be unique")


@dataclass(frozen=True, slots=True)
class RelatedElement:
    screen_id: str
    element: str
    bbox: NormalizedBBox

    def __post_init__(self) -> None:
        if not self.screen_id.strip() or not self.element.strip():
            raise ValueError("related element fields are required")
        object.__setattr__(self, "bbox", _normalized_bbox(self.bbox, "related_elements[].bbox"))

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RelatedElement":
        if not isinstance(value, dict) or set(value) != {"screen_id", "element", "bbox"}:
            raise ValueError("invalid related element fields")
        return cls(value["screen_id"], value["element"], value["bbox"])


@dataclass(frozen=True, slots=True)
class Detection:
    risk_type: RiskType
    risk_name: str
    where: DetectionLocation
    bbox: NormalizedBBox
    related_elements: tuple[RelatedElement, ...]
    what: str
    observation: str
    rule_id: str
    why: str
    severity: Severity
    confidence: float
    fix: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "bbox", _normalized_bbox(self.bbox))
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if self.rule_id != RISK_RULE_MAP[self.risk_type] or self.risk_name != RISK_NAME_MAP[self.risk_type]:
            raise ValueError("invalid risk mapping")
        if self.severity is not BASE_SEVERITY_MAP[self.risk_type]:
            raise ValueError("severity must equal the Rule Base base_severity")
        if any(not getattr(self, name).strip() for name in ("what", "observation", "why", "fix")):
            raise ValueError("narrative fields are required")

        if self.risk_type is not RiskType.SEQUENTIAL_PRICE_DISCLOSURE and len(self.where.screen_ids) != 1:
            raise ValueError(f"{self.rule_id} requires exactly one screen")
        if self.risk_type is RiskType.SEQUENTIAL_PRICE_DISCLOSURE and len(self.where.screen_ids) < 2:
            raise ValueError("DA-15 requires at least two distinct screens")

        if any(item.screen_id not in self.where.screen_ids for item in self.related_elements):
            raise ValueError("related elements must reference evidence screens in where.screen_ids")
        if self.risk_type is RiskType.VISUAL_HIERARCHY_DISTORTION:
            if not self.related_elements:
                raise ValueError("DA-03 requires a related counterpart element")
            primary_screen = self.where.screen_ids[0]
            if any(item.screen_id != primary_screen for item in self.related_elements):
                raise ValueError("DA-03 related elements must be on the primary screen")
            if any(item.element == self.where.element and item.bbox == self.bbox for item in self.related_elements):
                raise ValueError("DA-03 primary and related elements must be distinct")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Detection":
        fields = {
            "risk_type", "risk_name", "where", "bbox", "related_elements", "what",
            "observation", "rule_id", "why", "severity", "confidence", "fix",
        }
        if not isinstance(value, dict) or set(value) != fields:
            raise ValueError("invalid detection fields")
        where = value["where"]
        if not isinstance(where, dict) or set(where) != {"screen_ids", "element", "location"}:
            raise ValueError("invalid where fields")
        related = value["related_elements"]
        if not isinstance(related, list):
            raise ValueError("related_elements must be an array")
        return cls(
            risk_type=RiskType(value["risk_type"]),
            risk_name=value["risk_name"],
            where=DetectionLocation(tuple(where["screen_ids"]), where["element"], where["location"]),
            bbox=value["bbox"],
            related_elements=tuple(RelatedElement.from_dict(item) for item in related),
            what=value["what"],
            observation=value["observation"],
            rule_id=value["rule_id"],
            why=value["why"],
            severity=Severity(value["severity"]),
            confidence=float(value["confidence"]),
            fix=value["fix"],
        )


@dataclass(frozen=True, slots=True)
class LLMAuditOutput:
    audit_id: str
    schema_version: str
    screens: tuple[ScreenReference, ...]
    detections: tuple[Detection, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "LLMAuditOutput":
        if not isinstance(value, dict) or set(value) != {"audit_id", "schema_version", "screens", "detections"}:
            raise ValueError("invalid output fields")
        if value["schema_version"] != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
        screens = tuple(ScreenReference(**screen) for screen in value["screens"])
        output = cls(
            value["audit_id"],
            value["schema_version"],
            screens,
            tuple(Detection.from_dict(item) for item in value["detections"]),
        )
        screen_map = {screen.screen_id: screen for screen in screens}
        if len(screen_map) != len(screens):
            raise ValueError("screen_id values must be unique")
        referenced_ids = (
            screen_id
            for finding in output.detections
            for screen_id in (*finding.where.screen_ids, *(item.screen_id for item in finding.related_elements))
        )
        if any(screen_id not in screen_map for screen_id in referenced_ids):
            raise ValueError("unknown screen_id reference")

        for finding in output.detections:
            if finding.risk_type is RiskType.SEQUENTIAL_PRICE_DISCLOSURE:
                profiles = {screen_map[screen_id].device_profile for screen_id in finding.where.screen_ids}
                if len(profiles) != 1:
                    raise ValueError("DA-15 evidence screens must use the same device profile")

        # One element may legitimately receive multiple labels, but the same Rule
        # must not be emitted twice for the same primary element.
        detection_keys = [
            (finding.rule_id, finding.where.screen_ids[-1], finding.bbox)
            for finding in output.detections
        ]
        if len(detection_keys) != len(set(detection_keys)):
            raise ValueError("duplicate Rule detection for the same element")
        return output

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
