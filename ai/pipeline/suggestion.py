"""Remediation suggestion selection."""

from typing import Any

from ai.schemas.audit_output import AuditFinding


class SuggestionGenerator:
    def apply(self, finding: AuditFinding, rule: dict[str, Any]) -> AuditFinding:
        finding.suggestion = rule.get("fix_template") or f"'{finding.rule_name}' 위험을 유발한 강조·문구·선택 구조를 중립적으로 재설계하세요."
        return finding
