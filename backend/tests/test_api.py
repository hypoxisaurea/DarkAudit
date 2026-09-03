from __future__ import annotations

import base64
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_temp_root = Path(tempfile.mkdtemp(prefix="darkaudit-api-test-"))
os.environ["DARKAUDIT_DB_URL"] = f"sqlite:///{(_temp_root / 'test.db').as_posix()}"
os.environ["DARKAUDIT_PROVIDER"] = "fake"

from fastapi.testclient import TestClient

from ai.browser.models import CaptureArtifact, CaptureResult, ScanMode
from ai.pipeline.web_audit import URLAuditResult, URLCaptureResult
from ai.schemas.audit_schema import (
    LLMAuditOutput,
    RISK_NAME_MAP,
    RiskType,
    ScreenReference,
)
from backend.api import service

service.DATA_DIR = _temp_root
service.UPLOAD_DIR = _temp_root / "uploads"
service.CAPTURE_DIR = _temp_root / "captures"

from backend.api.main import app


class DetectingProvider:
    def analyze(self, request, system_prompt, audit_prompt, rules, output_schema):
        screen = request.screens[0]
        return {
            "audit_id": request.audit_id,
            "schema_version": request.schema_version,
            "screens": [
                {"screen_id": item.screen_id, "flow_step": item.flow_step}
                for item in request.screens
            ],
            "detections": [
                {
                    "risk_type": RiskType.PRESELECTED_OPTION.value,
                    "risk_name": RISK_NAME_MAP[RiskType.PRESELECTED_OPTION],
                    "where": {
                        "screen_ids": [screen.screen_id],
                        "element": "해외 치료비 보장",
                        "location": "추가 보장 선택 영역",
                    },
                    "what": "유료 선택 항목이 미리 선택되어 있습니다.",
                    "observation": "체크박스가 선택 상태로 표시됩니다.",
                    "rule_id": "DA-04",
                    "why": "사용자가 추가 비용을 그대로 수용할 수 있습니다.",
                    "severity": "HIGH",
                    "confidence": 0.92,
                    "fix": "초기 상태를 미선택으로 변경합니다.",
                }
            ],
        }


class ApiIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client_context.__exit__(None, None, None)
        shutil.rmtree(_temp_root, ignore_errors=True)

    def test_uploaded_audit_runs_pipeline_and_persists_finding(self) -> None:
        created = self.client.post(
            "/api/v1/audits",
            json={"name": "보험 가입 진단", "platform": "mobile-web"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        audit_id = created.json()["id"]

        image = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        uploaded = self.client.post(
            f"/api/v1/audits/{audit_id}/screens",
            files={"files": ("option.png", image, "image/png")},
            data={"screen_ids": "option", "flow_steps": "추가 보장 선택"},
        )
        self.assertEqual(uploaded.status_code, 200, uploaded.text)
        self.assertEqual(uploaded.json()["screens"][0]["flowStep"], "추가 보장 선택")

        with patch("backend.api.service.create_provider", return_value=DetectingProvider()):
            queued = self.client.post(f"/api/v1/audits/{audit_id}/analyze")
        self.assertEqual(queued.status_code, 202, queued.text)
        job = self.client.get(f"/api/v1/analysis-jobs/{queued.json()['jobId']}").json()
        self.assertEqual(job["status"], "completed", job)

        dashboard = self.client.get("/api/v1/dashboard/summary")
        self.assertEqual(dashboard.status_code, 200, dashboard.text)
        audit = dashboard.json()["audits"][0]
        self.assertRegex(audit["updatedAt"], r"(?:Z|\+00:00)$")
        self.assertEqual(audit["status"], "completed")
        self.assertEqual(len(audit["findings"]), 1)
        finding = audit["findings"][0]
        self.assertEqual(finding["ruleId"], "DA-04")
        self.assertEqual(finding["element"], "해외 치료비 보장")

        resolved = self.client.patch(
            f"/api/v1/findings/{finding['id']}", json={"status": "resolved"}
        )
        self.assertEqual(resolved.status_code, 200, resolved.text)

    def test_url_capture_persists_selected_screens(self) -> None:
        audit_id = self.client.post(
            "/api/v1/audits",
            json={"name": "URL 진단", "platform": "mobile-web"},
        ).json()["id"]
        image_path = service.CAPTURE_DIR / "captured.png"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(b"capture")
        artifact = CaptureArtifact(
            screen_id="mobile-initial",
            flow_step="mobile: initial viewport",
            profile="mobile",
            url="https://example.com",
            title="Example",
            image_path=image_path,
            viewport_width=393,
            viewport_height=852,
        )
        result = URLAuditResult(
            URLCaptureResult(
                audit_id=audit_id,
                url="https://example.com",
                mode=ScanMode.QUICK,
                profiles=(
                    CaptureResult(
                        audit_id=audit_id,
                        profile="mobile",
                        mode=ScanMode.QUICK,
                        artifacts=(artifact,),
                        stop_reason="quick capture completed",
                    ),
                ),
            ),
            LLMAuditOutput(
                audit_id=audit_id,
                schema_version="1.0",
                screens=(ScreenReference("mobile-initial", "mobile: initial viewport"),),
                detections=(),
            ),
        )

        with (
            patch("backend.api.main.UrlSafetyPolicy.validate", return_value="https://example.com"),
            patch("backend.api.service.URLCapturePipeline.run", return_value=result.capture),
            patch("backend.api.service.BaselineAuditPipeline.analyze", return_value=result.analysis),
        ):
            queued = self.client.post(
                f"/api/v1/audits/{audit_id}/capture",
                json={
                    "url": "https://example.com",
                    "mode": "quick",
                    "profiles": ["mobile"],
                },
            )
        self.assertEqual(queued.status_code, 202, queued.text)
        job = self.client.get(f"/api/v1/analysis-jobs/{queued.json()['jobId']}").json()
        self.assertEqual(job["status"], "completed", job)
        audit = self.client.get("/api/v1/dashboard/summary").json()["audits"][0]
        self.assertEqual(audit["screens"][0]["flowStep"], "mobile: initial viewport")
        self.assertEqual(audit["screens"][0]["width"], 393)

    def test_rejects_analysis_without_uploaded_screens(self) -> None:
        audit_id = self.client.post(
            "/api/v1/audits",
            json={"name": "빈 진단", "platform": "desktop-web"},
        ).json()["id"]
        response = self.client.post(f"/api/v1/audits/{audit_id}/analyze")
        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
