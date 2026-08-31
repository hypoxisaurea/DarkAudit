"""Output contracts shared by the detector and API layer."""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    LOW = "LOW"
    REVIEW = "REVIEW"
    HIGH = "HIGH"


@dataclass(slots=True)
class Evidence:
    screen_id: str
    description: str
    value: Any = None


@dataclass(slots=True)
class AuditFinding:
    rule_id: str
    rule_name: str
    category: str
    severity: Severity
    confidence: float
    rationale: str
    evidence: list[Evidence] = field(default_factory=list)
    suggestion: str | None = None


@dataclass(slots=True)
class AuditOutput:
    audit_id: str
    findings: list[AuditFinding]
    model_version: str = "scaffold-v1"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
