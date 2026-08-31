"""Input contracts for a UI audit."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ScreenInput:
    screen_id: str
    image_path: str | Path | None = None
    text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.image_path is None and not self.text:
            raise ValueError("A screen requires image_path or text")
        if self.image_path is not None:
            self.image_path = Path(self.image_path)


@dataclass(slots=True)
class AuditInput:
    audit_id: str
    screens: list[ScreenInput]
    product_type: str | None = None
    locale: str = "ko-KR"
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.screens:
            raise ValueError("At least one screen is required")
