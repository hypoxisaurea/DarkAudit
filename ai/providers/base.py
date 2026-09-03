"""Provider boundary for multimodal model vendors."""
from typing import Any, Protocol
from ai.schemas.audit_schema import LLMAuditRequest

class MultimodalProvider(Protocol):
    def analyze(self, request: LLMAuditRequest, system_prompt: str, audit_prompt: str,
                rules: list[dict[str, Any]], output_schema: dict[str, Any],
                candidates: list[dict[str, Any]] | None = None) -> dict[str, Any]: ...
