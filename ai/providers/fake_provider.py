"""Deterministic provider used for local integration tests."""
from typing import Any
from ai.schemas.audit_schema import LLMAuditRequest

class FakeMultimodalProvider:
    def analyze(self, request: LLMAuditRequest, system_prompt: str, audit_prompt: str,
                rules: list[dict[str, Any]], output_schema: dict[str, Any],
                candidates: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        return {"audit_id": request.audit_id, "schema_version": request.schema_version,
                "screens": [{"screen_id": s.screen_id, "flow_step": s.flow_step} for s in request.screens],
                "detections": []}
