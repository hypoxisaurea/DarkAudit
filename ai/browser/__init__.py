"""Safe browser acquisition for URL-based DarkAudit runs."""

from .explorer import HybridWebExplorer
from .models import (
    BrowserAction,
    BrowserActionType,
    CaptureArtifact,
    CaptureResult,
    ComputerTurn,
    ScanMode,
)
from .playwright_driver import PlaywrightSessionFactory
from .profiles import DeviceProfile, get_device_profile
from .safety import ActionSafetyPolicy, UrlSafetyPolicy

__all__ = [
    "ActionSafetyPolicy",
    "BrowserAction",
    "BrowserActionType",
    "CaptureArtifact",
    "CaptureResult",
    "ComputerTurn",
    "DeviceProfile",
    "HybridWebExplorer",
    "PlaywrightSessionFactory",
    "ScanMode",
    "UrlSafetyPolicy",
    "get_device_profile",
]
