"""OpenAI Responses API adapter with strict JSON Schema output."""
import base64
import json
import mimetypes
from typing import Any
from ai.schemas.audit_schema import LLMAuditRequest

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

    @staticmethod
    def _data_url(path: Any) -> str:
        mime = mimetypes.guess_type(str(path))[0] or "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    def analyze(self, request: LLMAuditRequest, system_prompt: str, audit_prompt: str,
                rules: list[dict[str, Any]], output_schema: dict[str, Any]) -> dict[str, Any]:
        content: list[dict[str, Any]] = [{"type": "input_text", "text": audit_prompt}]
        for screen in request.screens:
            content.append({"type": "input_text", "text": f"screen_id={screen.screen_id}; flow_step={screen.flow_step}"})
            content.append({"type": "input_image", "image_url": self._data_url(screen.image_path), "detail": "high"})
        content.append({"type": "input_text", "text": "Rule Context:\n" + json.dumps(rules, ensure_ascii=False)})
        response = self.client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=[{"role": "user", "content": content}],
            text={"format": {"type": "json_schema", "name": "darkaudit_output", "schema": output_schema, "strict": True}},
        )
        if not getattr(response, "output_text", None):
            raise RuntimeError("Model returned no output_text")
        return json.loads(response.output_text)
