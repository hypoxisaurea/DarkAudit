import os
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
import backend.service as service
from backend.main import app
from backend.storage import STORE

class ApiIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        service.UPLOAD_ROOT = Path(self.temp.name)
        os.environ["DARKAUDIT_PROVIDER"] = "fake"
        with STORE.lock:
            STORE.audits.clear()
            STORE.jobs.clear()
        self.client = TestClient(app)

    def tearDown(self): self.temp.cleanup()

    def test_create_upload_analyze_and_dashboard(self):
        created = self.client.post("/api/v1/audits", json={"name": "보험 가입", "platform": "mobile-web"})
        self.assertEqual(created.status_code, 201)
        audit_id = created.json()["id"]
        uploaded = self.client.post(
            f"/api/v1/audits/{audit_id}/screens",
            files=[("files", ("screen.png", b"png", "image/png"))],
            data={"screen_ids": "screen-01", "flow_steps": "상품안내"},
        )
        self.assertEqual(uploaded.status_code, 200)
        started = self.client.post(f"/api/v1/audits/{audit_id}/analyze")
        self.assertEqual(started.status_code, 202)
        job = self.client.get(f"/api/v1/analysis-jobs/{started.json()['jobId']}").json()
        self.assertEqual(job["status"], "completed")
        summary = self.client.get("/api/v1/dashboard/summary").json()
        self.assertEqual(summary["activeAuditId"], audit_id)
        self.assertEqual(summary["audits"][0]["status"], "completed")

if __name__ == "__main__": unittest.main()
