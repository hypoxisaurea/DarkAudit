"""Screenshot-to-structured-JSON MVP baseline."""
import json
from pathlib import Path
from ai.providers.base import MultimodalProvider
from ai.rules.rule_loader import RuleLoader
from ai.schemas.audit_schema import LLMAuditOutput, LLMAuditRequest
from .response_parser import parse_audit_response

MVP_RULE_IDS = {"DA-03", "DA-04", "DA-12", "DA-15"}

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

    def analyze(self, request: LLMAuditRequest) -> LLMAuditOutput:
        arguments = {
            "request": request,
            "system_prompt": (self.prompts_dir / "system.md").read_text(encoding="utf-8"),
            "audit_prompt": (self.prompts_dir / "audit_v1.md").read_text(encoding="utf-8"),
            "rules": self.rule_loader.rules(rule_ids=MVP_RULE_IDS),
            "output_schema": json.loads(self.schema_path.read_text(encoding="utf-8")),
        }
        last_error: ValueError | None = None
        for _ in range(self.max_attempts):
            try:
                return parse_audit_response(self.provider.analyze(**arguments), request)
            except ValueError as exc:
                last_error = exc
        raise ValueError(f"Model output failed validation after {self.max_attempts} attempts") from last_error
