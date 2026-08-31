"""Validated access to the canonical rule base."""

import json
from pathlib import Path
from typing import Any


class RuleLoader:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else Path(__file__).parents[2] / "rules" / "dark_pattern_rules.yaml"

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            raise FileNotFoundError(f"Rule base not found: {self.path}")
        if self.path.suffix.lower() == ".json":
            document = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            try:
                import yaml
            except ImportError as exc:
                raise RuntimeError("Loading YAML rules requires PyYAML: pip install pyyaml") from exc
            document = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        self._validate(document)
        return document

    def rules(self, priority: str | None = None, rule_ids: set[str] | None = None) -> list[dict[str, Any]]:
        rules = self.load()["rules"]
        return [rule for rule in rules if (priority is None or rule["mvp_priority"] == priority)
                and (rule_ids is None or rule["rule_id"] in rule_ids)]

    @staticmethod
    def _validate(document: Any) -> None:
        if not isinstance(document, dict) or not isinstance(document.get("rules"), list):
            raise ValueError("Rule base must contain a 'rules' list")
        ids = [rule.get("rule_id") for rule in document["rules"]]
        if any(not rule_id for rule_id in ids) or len(ids) != len(set(ids)):
            raise ValueError("Every rule must have a unique rule_id")
