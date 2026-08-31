from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class CreateAuditRequest(BaseModel):
    name: str = Field(min_length=1)
    platform: Literal["mobile-web", "desktop-web", "app"]

class ScreenDto(BaseModel):
    id: str
    order: int
    flowStep: str
    imageUrl: str
    findingCount: int = 0

class FindingDto(BaseModel):
    id: str
    ruleId: Literal["DA-03", "DA-04", "DA-12", "DA-15"]
    riskType: Literal["PRESELECTED_OPTION", "VISUAL_HIERARCHY_DISTORTION", "EMOTIONAL_LANGUAGE", "SEQUENTIAL_PRICE_DISCLOSURE"]
    title: str
    description: str
    screenIds: list[str]
    element: str
    defaultState: str | None = None
    costImpact: str | None = None
    severity: Literal["HIGH", "REVIEW"]
    status: Literal["open", "reviewing", "resolved"] = "open"
    confidence: float = Field(ge=0, le=1)
    recommendation: str
    guideline: str

class AuditDto(BaseModel):
    id: str
    name: str
    platform: Literal["mobile-web", "desktop-web", "app"]
    status: Literal["draft", "queued", "analyzing", "completed", "failed"]
    updatedAt: datetime
    screens: list[ScreenDto]
    findings: list[FindingDto]

class JobDto(BaseModel):
    jobId: str
    auditId: str
    status: Literal["queued", "analyzing", "completed", "failed"]
    progress: float = Field(ge=0, le=100)

class FindingStatusRequest(BaseModel):
    status: Literal["open", "reviewing", "resolved"]
