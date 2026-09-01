import unittest

from ai.browser.models import BrowserAction, BrowserActionType
from ai.browser.safety import (
    ActionSafetyPolicy,
    UnsafeActionError,
    UnsafeUrlError,
    UrlSafetyPolicy,
)


class UrlSafetyPolicyTest(unittest.TestCase):
    def test_accepts_public_http_url(self):
        policy = UrlSafetyPolicy(resolver=lambda _: ["93.184.216.34"])
        self.assertEqual(policy.validate("https://example.com/product"), "https://example.com/product")

    def test_blocks_private_address(self):
        policy = UrlSafetyPolicy(resolver=lambda _: ["127.0.0.1"])
        with self.assertRaises(UnsafeUrlError):
            policy.validate("http://localhost:8000")

    def test_blocks_cross_origin_navigation(self):
        policy = UrlSafetyPolicy(resolver=lambda _: ["93.184.216.34"])
        with self.assertRaises(UnsafeUrlError):
            policy.validate_same_origin("https://other.example/path", "https://example.com")


class ActionSafetyPolicyTest(unittest.TestCase):
    def test_allows_reversible_scroll(self):
        ActionSafetyPolicy().validate(
            BrowserAction(BrowserActionType.SCROLL, x=100, y=100, scroll_y=600),
            viewport_width=390,
            viewport_height=844,
        )

    def test_blocks_typing(self):
        with self.assertRaises(UnsafeActionError):
            ActionSafetyPolicy().validate(
                BrowserAction(BrowserActionType.TYPE, text="secret"),
                viewport_width=390,
                viewport_height=844,
            )

    def test_blocks_consequential_click(self):
        with self.assertRaises(UnsafeActionError):
            ActionSafetyPolicy().validate(
                BrowserAction(BrowserActionType.CLICK, x=10, y=10),
                viewport_width=390,
                viewport_height=844,
                target={"tag": "button", "text": "결제하기"},
            )


if __name__ == "__main__":
    unittest.main()
