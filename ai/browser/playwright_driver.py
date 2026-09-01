"""Playwright-backed browser session with network isolation checks."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from types import TracebackType
from typing import Any
from urllib.parse import urlsplit

from .models import BrowserAction, BrowserActionType, CaptureArtifact
from .profiles import DeviceProfile
from .safety import UnsafeUrlError, UrlSafetyPolicy


def _safe_segment(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")
    if not cleaned:
        raise ValueError("Artifact path segment cannot be empty")
    return cleaned[:80]


class PlaywrightSessionFactory:
    def __init__(
        self,
        output_root: str | Path,
        *,
        url_policy: UrlSafetyPolicy | None = None,
        headless: bool = True,
        navigation_timeout_ms: int = 30_000,
        settle_time_ms: int = 750,
    ) -> None:
        self.output_root = Path(output_root)
        self.url_policy = url_policy or UrlSafetyPolicy()
        self.headless = headless
        self.navigation_timeout_ms = navigation_timeout_ms
        self.settle_time_ms = settle_time_ms

    def __call__(self, audit_id: str, profile: DeviceProfile) -> "PlaywrightBrowserSession":
        target = self.output_root / _safe_segment(audit_id) / _safe_segment(profile.name)
        return PlaywrightBrowserSession(
            profile,
            target,
            url_policy=self.url_policy,
            headless=self.headless,
            navigation_timeout_ms=self.navigation_timeout_ms,
            settle_time_ms=self.settle_time_ms,
        )


class PlaywrightBrowserSession:
    def __init__(
        self,
        profile: DeviceProfile,
        output_dir: Path,
        *,
        url_policy: UrlSafetyPolicy,
        headless: bool,
        navigation_timeout_ms: int,
        settle_time_ms: int,
    ) -> None:
        self.profile = profile
        self.output_dir = output_dir
        self.url_policy = url_policy
        self.headless = headless
        self.navigation_timeout_ms = navigation_timeout_ms
        self.settle_time_ms = settle_time_ms
        self._manager: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._origin_url: str | None = None
        self._artifact_index = 0
        self._blocked_reason: str | None = None
        self._validated_hosts: set[str] = set()

    def __enter__(self) -> "PlaywrightBrowserSession":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            ) from exc

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._manager = sync_playwright().start()
        self._browser = self._manager.chromium.launch(
            headless=self.headless,
            args=["--disable-extensions", "--disable-dev-shm-usage"],
        )
        options: dict[str, Any] = {}
        if self.profile.playwright_device:
            options.update(self._manager.devices.get(self.profile.playwright_device, {}))
        options.update(
            {
                "viewport": {
                    "width": self.profile.viewport_width,
                    "height": self.profile.viewport_height,
                },
                "device_scale_factor": self.profile.device_scale_factor,
                "is_mobile": self.profile.is_mobile,
                "has_touch": self.profile.has_touch,
                "locale": "ko-KR",
                "timezone_id": "Asia/Seoul",
                "accept_downloads": False,
            }
        )
        self._context = self._browser.new_context(**options)
        self._page = self._context.new_page()
        self._page.set_default_timeout(10_000)
        self._page.route("**/*", self._route_request)
        self._context.on("page", lambda popup: popup.close() if popup != self._page else None)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._context is not None:
            self._context.close()
        if self._browser is not None:
            self._browser.close()
        if self._manager is not None:
            self._manager.stop()

    def start(self, url: str) -> CaptureArtifact:
        self.url_policy.validate(url)
        # Permit the initial public redirect chain (for example http -> https),
        # then lock smart exploration to the final origin.
        self._origin_url = None
        try:
            self._page.goto(url, wait_until="domcontentloaded", timeout=self.navigation_timeout_ms)
        except Exception as exc:
            if self._blocked_reason:
                raise UnsafeUrlError(self._blocked_reason) from exc
            raise
        self._settle()
        self.url_policy.validate(self._page.url)
        self._origin_url = self._page.url
        self._validate_current_url()
        return self.capture("initial viewport")

    def capture(
        self,
        flow_step: str,
        *,
        full_page: bool = False,
        action: BrowserAction | None = None,
    ) -> CaptureArtifact:
        self._validate_current_url()
        index = self._artifact_index
        self._artifact_index += 1
        slug = _safe_segment(flow_step.lower().replace(" ", "-"))
        path = self.output_dir / f"{index:02d}-{slug}.png"
        image = self._page.screenshot(
            path=str(path),
            full_page=full_page,
            animations="disabled",
            caret="hide",
            scale="css",
        )
        visible_text = self._visible_text()
        elements = tuple(self._interactive_elements())
        return CaptureArtifact(
            screen_id=f"{self.profile.name}_{index:02d}",
            flow_step=f"{self.profile.name}: {flow_step}",
            profile=self.profile.name,
            url=self._page.url,
            title=self._page.title(),
            image_path=path,
            viewport_width=self.profile.viewport_width,
            viewport_height=self.profile.viewport_height,
            full_page=full_page,
            action=action,
            visible_text=visible_text,
            interactive_elements=elements,
            fingerprint=hashlib.sha256(image).hexdigest(),
        )

    def execute(self, action: BrowserAction) -> None:
        match action.type:
            case BrowserActionType.CLICK:
                self._page.mouse.click(action.x, action.y, button=action.button)
            case BrowserActionType.SCROLL:
                self._page.mouse.move(action.x, action.y)
                self._page.mouse.wheel(action.scroll_x, action.scroll_y)
            case BrowserActionType.WAIT:
                self._page.wait_for_timeout(1_000)
            case BrowserActionType.KEYPRESS:
                for key in action.keys:
                    self._page.keyboard.press(_normalize_key(key))
            case BrowserActionType.MOVE:
                self._page.mouse.move(action.x, action.y)
            case BrowserActionType.SCREENSHOT:
                return
            case _:
                raise ValueError(f"Unsupported action: {action.type.value}")
        self._settle()
        self._validate_current_url()

    def inspect_target(self, action: BrowserAction) -> dict[str, Any] | None:
        if action.x is None or action.y is None:
            return None
        return self._page.evaluate(
            """
            ({x, y}) => {
              const hit = document.elementFromPoint(x, y);
              if (!hit) return null;
              const element = hit.closest('button,a,input,select,textarea,[role="button"],[role="link"]') || hit;
              return {
                tag: element.tagName.toLowerCase(),
                type: element.getAttribute('type') || '',
                text: (element.innerText || element.textContent || '').trim().slice(0, 300),
                ariaLabel: element.getAttribute('aria-label') || '',
                title: element.getAttribute('title') || '',
                value: element.getAttribute('value') || '',
                href: element.href || ''
              };
            }
            """,
            {"x": action.x, "y": action.y},
        )

    def _route_request(self, route: Any, request: Any) -> None:
        parsed = urlsplit(request.url)
        if parsed.scheme not in {"http", "https"}:
            if parsed.scheme in {"data", "blob", "about"}:
                route.continue_()
            else:
                route.abort("blockedbyclient")
            return
        try:
            hostname = parsed.hostname or ""
            if hostname not in self._validated_hosts:
                self.url_policy.validate(request.url)
                self._validated_hosts.add(hostname)
            if (
                self._origin_url
                and request.is_navigation_request()
                and request.frame == self._page.main_frame
            ):
                self.url_policy.validate_same_origin(request.url, self._origin_url)
        except UnsafeUrlError as exc:
            self._blocked_reason = str(exc)
            route.abort("blockedbyclient")
            return
        route.continue_()

    def _validate_current_url(self) -> None:
        if self._blocked_reason:
            raise UnsafeUrlError(self._blocked_reason)
        if self._origin_url:
            self.url_policy.validate_same_origin(self._page.url, self._origin_url)

    def _settle(self) -> None:
        try:
            self._page.wait_for_load_state("domcontentloaded", timeout=5_000)
        except Exception:
            pass
        self._page.wait_for_timeout(self.settle_time_ms)

    def _visible_text(self) -> str:
        try:
            return self._page.locator("body").inner_text(timeout=3_000)[:12_000]
        except Exception:
            return ""

    def _interactive_elements(self) -> list[dict[str, Any]]:
        try:
            return self._page.evaluate(
                """
                () => Array.from(document.querySelectorAll(
                  'a,button,input,select,textarea,[role="button"],[role="link"],[role="checkbox"],[role="radio"]'
                )).filter((element) => {
                  const rect = element.getBoundingClientRect();
                  const style = getComputedStyle(element);
                  return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
                }).slice(0, 100).map((element) => {
                  const rect = element.getBoundingClientRect();
                  return {
                    tag: element.tagName.toLowerCase(),
                    role: element.getAttribute('role') || '',
                    type: element.getAttribute('type') || '',
                    text: (element.innerText || element.value || element.textContent || '').trim().slice(0, 300),
                    ariaLabel: element.getAttribute('aria-label') || '',
                    checked: 'checked' in element ? Boolean(element.checked) : null,
                    disabled: 'disabled' in element ? Boolean(element.disabled) : null,
                    href: element.href || '',
                    box: {x: rect.x, y: rect.y, width: rect.width, height: rect.height}
                  };
                })
                """
            )
        except Exception:
            return []


def _normalize_key(key: str) -> str:
    mapping = {
        "ESC": "Escape",
        "ESCAPE": "Escape",
        "TAB": "Tab",
        "ARROWUP": "ArrowUp",
        "ARROWDOWN": "ArrowDown",
        "PAGEUP": "PageUp",
        "PAGEDOWN": "PageDown",
    }
    return mapping.get(key.upper(), key)
