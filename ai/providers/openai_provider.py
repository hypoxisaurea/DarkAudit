"""OpenAI Responses API adapter with strict JSON Schema output."""
import base64
import json
import mimetypes
from typing import Any
from ai.schemas.audit_schema import LLMAuditRequest


def _responses_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Remove conditional JSON Schema keywords unsupported by Structured Outputs.

    The domain parser validates these cross-field constraints after generation, so
    removing them here changes only the API-facing schema, not output validation.
    """
    unsupported = {"allOf", "if", "then", "else"}
    normalized = {
        key: (
            _responses_schema(value)
            if isinstance(value, dict)
            else [_responses_schema(item) if isinstance(item, dict) else item for item in value]
            if isinstance(value, list)
            else value
        )
        for key, value in schema.items()
        if key not in unsupported
    }
    if "const" in normalized and "type" not in normalized:
        value = normalized["const"]
        normalized["type"] = (
            "boolean" if isinstance(value, bool)
            else "integer" if isinstance(value, int)
            else "number" if isinstance(value, float)
            else "string"
        )
    return normalized

class OpenAIResponsesProvider:
    def __init__(self, model: str, client: Any | None = None) -> None:
        if not model.strip(): raise ValueError("model is required")
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError("Install the OpenAI SDK: pip install openai") from exc
            client = OpenAI()
        self.client = client
        self.model = model
        self.last_usage: dict[str, int] | None = None

    @staticmethod
    def _data_url(path: Any) -> str:
        mime = mimetypes.guess_type(str(path))[0] or "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    def analyze(self, request: LLMAuditRequest, system_prompt: str, audit_prompt: str,
                rules: list[dict[str, Any]], output_schema: dict[str, Any],
                candidates: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        content: list[dict[str, Any]] = [
            {"type": "input_text", "text": audit_prompt},
            {
                "type": "input_text",
                "text": (
                    f"Copy these request identity fields exactly into the response: "
                    f"audit_id={request.audit_id}; schema_version={request.schema_version}"
                ),
            },
        ]
        for screen in request.screens:
            content.append({"type": "input_text", "text": f"screen_id={screen.screen_id}; flow_step={screen.flow_step}"})
            content.append({"type": "input_image", "image_url": self._data_url(screen.image_path), "detail": "high"})
        content.append({"type": "input_text", "text": "Rule Context:\n" + json.dumps(rules, ensure_ascii=False)})
        content.append({
            "type": "input_text",
            "text": "Deterministic Candidates (signals, not conclusions):\n" + json.dumps(
                candidates or [], ensure_ascii=False
            ),
        })
        response = self.client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=[{"role": "user", "content": content}],
            text={"format": {"type": "json_schema", "name": "darkaudit_output", "schema": _responses_schema(output_schema), "strict": True}},
        )
        usage = getattr(response, "usage", None)
        self.last_usage = None if usage is None else {
            "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
            "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        }
        if not getattr(response, "output_text", None):
            raise RuntimeError("Model returned no output_text")
        return json.loads(response.output_text)
