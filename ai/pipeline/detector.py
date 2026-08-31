"""Rule candidate detection. Production semantic checks can be injected later."""

from collections.abc import Iterable
from typing import Any

from ai.schemas.audit_output import AuditFinding, Evidence, Severity
from ai.vision.ui_parser import UIElement


class RuleDetector:
    def detect(self, rule: dict[str, Any], screens: dict[str, list[UIElement]]) -> AuditFinding | None:
        check_ids = {str(value) for values in screens.values() for element in values for value in element.attributes.get("matched_checks", [])}
        matched = [check for check in rule.get("deterministic_checks", []) if check.get("id") in check_ids]
        if not matched:
            return None
        severity = Severity.HIGH if rule.get("standalone_sufficient", True) else Severity.REVIEW
        evidence = self._evidence(matched, screens)
        return AuditFinding(
            rule_id=rule["rule_id"],
            rule_name=rule["official_name_ko"],
            category=rule["category"],
            severity=severity,
            confidence=min(0.95, 0.55 + 0.1 * len(matched)),
            rationale="; ".join(check["desc"] for check in matched),
            evidence=evidence,
        )

    @staticmethod
    def _evidence(matched: Iterable[dict[str, Any]], screens: dict[str, list[UIElement]]) -> list[Evidence]:
        ids = {check["id"] for check in matched}
        return [
            Evidence(screen_id=screen_id, description=f"deterministic check: {check_id}")
            for screen_id, elements in screens.items()
            for element in elements
            for check_id in element.attributes.get("matched_checks", [])
            if check_id in ids
        ]
