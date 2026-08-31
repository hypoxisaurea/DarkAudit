"""OCR provider boundary. Replace NullOCR with a production adapter."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(slots=True)
class OCRTextBlock:
    text: str
    bbox: tuple[int, int, int, int] | None = None
    confidence: float = 1.0


@dataclass(slots=True)
class OCRResult:
    blocks: list[OCRTextBlock] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(block.text for block in self.blocks)


class OCRProvider(Protocol):
    def extract(self, image_path: Path) -> OCRResult: ...


class NullOCR:
    """Safe default that makes missing OCR configuration explicit in results."""

    def extract(self, image_path: Path) -> OCRResult:
        if not image_path.exists():
            raise FileNotFoundError(image_path)
        return OCRResult()
