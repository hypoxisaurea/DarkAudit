"""Interfaces that keep orchestration testable without a real browser."""

from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Any, Protocol

from .models import BrowserAction, CaptureArtifact, ComputerTurn
from .profiles import DeviceProfile


class BrowserSession(Protocol):
    profile: DeviceProfile

    def __enter__(self) -> "BrowserSession": ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def start(self, url: str) -> CaptureArtifact: ...

    def capture(
        self,
        flow_step: str,
        *,
        full_page: bool = False,
        action: BrowserAction | None = None,
    ) -> CaptureArtifact: ...

    def execute(self, action: BrowserAction) -> None: ...

    def inspect_target(self, action: BrowserAction) -> dict[str, Any] | None: ...


class BrowserSessionFactory(Protocol):
    def __call__(self, audit_id: str, profile: DeviceProfile) -> BrowserSession: ...


class ComputerAgent(Protocol):
    def begin(self, goal: str) -> ComputerTurn: ...

    def resume(self, previous_turn: ComputerTurn, screenshot_path: Path) -> ComputerTurn: ...
