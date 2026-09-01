"""Stable browser profiles used by URL audits."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DeviceProfile:
    name: str
    viewport_width: int
    viewport_height: int
    is_mobile: bool
    has_touch: bool
    device_scale_factor: float = 1.0
    playwright_device: str | None = None


_PROFILES = {
    "desktop": DeviceProfile("desktop", 1440, 900, False, False),
    "mobile": DeviceProfile("mobile", 393, 852, True, True, 3.0, "Pixel 5"),
    "iphone": DeviceProfile("iphone", 390, 844, True, True, 3.0, "iPhone 13"),
}


def get_device_profile(name: str) -> DeviceProfile:
    try:
        return _PROFILES[name.lower()]
    except KeyError as exc:
        supported = ", ".join(sorted(_PROFILES))
        raise ValueError(f"Unsupported device profile {name!r}; choose one of: {supported}") from exc


def device_profile_names() -> tuple[str, ...]:
    return tuple(_PROFILES)
