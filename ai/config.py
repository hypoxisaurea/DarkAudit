"""Environment-backed AI runtime settings."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass(frozen=True, slots=True)
class AISettings:
    provider: str
    model: str | None
    computer_model: str | None = None

    @classmethod
    def from_env(cls) -> "AISettings":
        load_dotenv()
        return cls(
            os.getenv("DARKAUDIT_PROVIDER", "fake").lower(),
            os.getenv("DARKAUDIT_MODEL") or None,
            os.getenv("DARKAUDIT_COMPUTER_MODEL") or None,
        )
