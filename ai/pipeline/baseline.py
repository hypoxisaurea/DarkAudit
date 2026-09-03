"""Screenshot-to-structured-JSON MVP baseline."""
import json
import time
from pathlib import Path
from typing import Any
from ai.providers.base import MultimodalProvider
from ai.rules.rule_loader import RuleLoader
from ai.schemas.audit_schema import HybridAuditOutput, LLMAuditRequest, RuleCandidate
from .response_parser import parse_hybrid_response

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
        self, request: LLMAuditRequest,
        candidates: list[dict[str, Any] | RuleCandidate] | None = None,
    ) -> HybridAuditOutput:
        parsed_candidates = [
            item if isinstance(item, RuleCandidate) else RuleCandidate.from_dict(item)
            for item in (candidates or [])
        ]
        candidate_payload = [
            {
                "candidate_id": item.candidate_id,
                "rule_id": item.rule_id,
                "screen_id": item.screen_id,
                "screen_index": item.screen_index,
                "primary_element_id": item.primary_element_id,
                "triggered_checks": list(item.triggered_checks),
                "measurements": item.measurements,
                "related_element_ids": list(item.related_element_ids),
            }
            for item in parsed_candidates
        ]
        arguments = {
            "request": request,
            "system_prompt": (self.prompts_dir / "system.md").read_text(encoding="utf-8"),
            "audit_prompt": (self.prompts_dir / "audit_v1.md").read_text(encoding="utf-8"),
            "rules": self.rule_loader.rules(rule_ids=MVP_RULE_IDS),
            "output_schema": json.loads(self.schema_path.read_text(encoding="utf-8")),
            "candidates": candidate_payload,
        }
        last_error: ValueError | None = None
        started = time.perf_counter()
        for attempt in range(1, self.max_attempts + 1):
            try:
                raw = self.provider.analyze(**arguments)
                self._deduplicate_raw(raw)
                output = parse_hybrid_response(raw, request, parsed_candidates)
                result = self._filter_and_deduplicate(output)
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
        detections = raw.get("semantic_findings")
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
        raw["semantic_findings"] = [*kept.values(), *passthrough]

    @staticmethod
    def _filter_and_deduplicate(output: HybridAuditOutput) -> HybridAuditOutput:
        """Drop weak semantic-only claims and collapse duplicate findings."""
        kept = {}
        for finding in output.semantic_findings:
            key = (finding.rule_id, tuple(sorted(finding.where.screen_ids)))
            if finding.confidence < 0.70:
                continue
            duplicate_key = (key, finding.where.element.strip().casefold(), finding.bbox)
            previous = kept.get(duplicate_key)
            if previous is None or finding.confidence > previous.confidence:
                kept[duplicate_key] = finding
        return HybridAuditOutput(
            output.audit_id, output.schema_version, output.screens,
            output.candidate_decisions, tuple(kept.values()), output.candidates,
        )
