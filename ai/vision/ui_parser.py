"""Convert OCR and supplied metadata into normalized UI elements."""

from dataclasses import dataclass, field
from typing import Any

from .ocr import OCRResult


@dataclass(slots=True)
class UIElement:
    kind: str
    text: str = ""
    bbox: tuple[int, int, int, int] | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


class UIParser:
    def parse(self, ocr: OCRResult, metadata: dict[str, Any] | None = None) -> list[UIElement]:
        elements = [UIElement(kind="text", text=b.text, bbox=b.bbox, attributes={"confidence": b.confidence}) for b in ocr.blocks]
        for raw in (metadata or {}).get("elements", []):
            elements.append(UIElement(**raw))
        return elements
