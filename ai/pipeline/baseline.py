"""Screenshot-to-structured-JSON MVP baseline."""
import json
import time
from pathlib import Path
from typing import Any
from ai.providers.base import MultimodalProvider
from ai.rules.rule_loader import RuleLoader
from ai.schemas.audit_schema import LLMAuditOutput, LLMAuditRequest
from .response_parser import parse_audit_response

MVP_RULE_IDS = frozenset({"DA-03", "DA-04", "DA-12", "DA-15"})

class BaselineAuditPipeline:
    def __init__(self, provider: MultimodalProvider, rule_loader: RuleLoader | None = None,
                 prompts_dir: Path | None = None, schema_path: Path | None = None,
                 max_attempts: int = 2) -> None:
        root = Path(__file__).parents[1]
        self.provider = provider
        self.rule_loader = rule_loader or RuleLoader()
        self.prompts_dir = prompts_dir or root / "prompts"
        self.schema_path = schema_path or root / "schemas" / "audit_output.schema.json"
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.max_attempts = max_attempts
        self.last_run_telemetry: dict[str, Any] = {}

    def analyze(
        self, request: LLMAuditRequest, candidates: list[dict[str, Any]] | None = None
    ) -> LLMAuditOutput:
        arguments = {
            "request": request,
            "system_prompt": (self.prompts_dir / "system.md").read_text(encoding="utf-8"),
            "audit_prompt": (self.prompts_dir / "audit_v1.md").read_text(encoding="utf-8"),
            "rules": self.rule_loader.rules(rule_ids=MVP_RULE_IDS),
            "output_schema": json.loads(self.schema_path.read_text(encoding="utf-8")),
        }
        if candidates:
            arguments["candidates"] = candidates
        last_error: ValueError | None = None
        started = time.perf_counter()
        for attempt in range(1, self.max_attempts + 1):
            try:
                raw = self.provider.analyze(**arguments)
                self._deduplicate_raw(raw)
                output = parse_audit_response(raw, request)
                result = self._filter_and_deduplicate(output, candidates or [])
                self.last_run_telemetry = {
                    "response_time_seconds": time.perf_counter() - started,
                    "screen_count": len(request.screens),
                    "schema_attempts": attempt,
                    "schema_retries": attempt - 1,
                    "usage": getattr(self.provider, "last_usage", None),
                }
                return result
            except ValueError as exc:
                last_error = exc
        self.last_run_telemetry = {
            "response_time_seconds": time.perf_counter() - started,
            "screen_count": len(request.screens),
            "schema_attempts": self.max_attempts,
            "schema_retries": max(0, self.max_attempts - 1),
            "failed": True,
        }
        raise ValueError(f"Model output failed validation after {self.max_attempts} attempts") from last_error

    @staticmethod
    def _deduplicate_raw(raw: dict[str, Any]) -> None:
        """Collapse provider duplicates before strict cross-record validation."""
        detections = raw.get("detections")
        if not isinstance(detections, list):
            return
        kept: dict[tuple, dict[str, Any]] = {}
        passthrough: list[Any] = []
        for item in detections:
            try:
                where = item["where"]
                key = (
                    item["rule_id"], tuple(sorted(where["screen_ids"])),
                    str(where["element"]).strip().casefold(), tuple(item["bbox"]),
                )
                previous = kept.get(key)
                if previous is None or float(item["confidence"]) > float(previous["confidence"]):
                    kept[key] = item
            except (KeyError, TypeError, ValueError):
                passthrough.append(item)
        raw["detections"] = [*kept.values(), *passthrough]

    @staticmethod
    def _filter_and_deduplicate(
        output: LLMAuditOutput, candidates: list[dict[str, Any]]
    ) -> LLMAuditOutput:
        """Drop weak/unsupported model claims and collapse duplicate findings.

        A deterministic signal permits REVIEW-level confidence (0.50). A finding
        discovered by semantics alone needs stronger model confidence (0.70).
        Structural evidence requirements are enforced by ``Detection`` itself.
        """
        candidate_keys = {
            (item.get("rule_id"), tuple(sorted(item.get("screen_ids") or [])))
            for item in candidates
        }
        kept = {}
        for finding in output.detections:
            key = (finding.rule_id, tuple(sorted(finding.where.screen_ids)))
            threshold = 0.50 if key in candidate_keys else 0.70
            if finding.confidence < threshold:
                continue
            duplicate_key = (key, finding.where.element.strip().casefold(), finding.bbox)
            previous = kept.get(duplicate_key)
            if previous is None or finding.confidence > previous.confidence:
                kept[duplicate_key] = finding
        return LLMAuditOutput(
            output.audit_id, output.schema_version, output.screens, tuple(kept.values())
        )
