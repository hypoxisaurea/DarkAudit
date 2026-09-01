"""FastAPI adapter consumed by the DarkAudit frontend."""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, Header, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ai.browser.models import ScanMode
from ai.browser.safety import UnsafeUrlError, UrlSafetyPolicy
from backend.app.models import Audit, Finding, FindingStatus, FlowType, RunStatus, Screen

from .schemas import (
    AuditDto,
    CaptureAuditRequest,
    CreateAuditRequest,
    DashboardSummaryDto,
    FindingStatusRequest,
    JobDto,
)
from .service import (
    DATA_DIR,
    UPLOAD_DIR,
    analyze_uploaded_screens,
    capture_and_analyze_url,
    create_job,
    get_job,
    next_run,
    public_image_path,
    rules_by_id,
)
from .store import SessionLocal, get_audit, init_db, list_audits, to_audit_dto

app = FastAPI(title="DarkAudit API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "DARKAUDIT_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
DATA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=DATA_DIR), name="artifacts")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/audits", response_model=AuditDto, status_code=status.HTTP_201_CREATED)
def create_audit(payload: CreateAuditRequest) -> AuditDto:
    with SessionLocal() as session:
        audit = Audit(name=payload.name.strip(), product_name=payload.platform)
        session.add(audit)
        session.commit()
        return to_audit_dto(session, audit, rules_by_id())


@app.get("/api/v1/dashboard/summary", response_model=DashboardSummaryDto)
def dashboard_summary() -> DashboardSummaryDto:
    with SessionLocal() as session:
        audits = [to_audit_dto(session, audit, rules_by_id()) for audit in list_audits(session)]
        return DashboardSummaryDto(activeAuditId=audits[0].id if audits else None, audits=audits)


@app.post("/api/v1/audits/{audit_id}/screens", response_model=AuditDto)
async def upload_screens(
    audit_id: str,
    files: list[UploadFile] = File(...),
    screen_ids: list[str] = Form(default=[]),
    flow_steps: list[str] = Form(default=[]),
    x_darkaudit_screen_metadata: str | None = Header(default=None),
) -> AuditDto:
    if not 1 <= len(files) <= 5:
        raise HTTPException(400, "1개에서 5개의 이미지가 필요합니다.")
    metadata = []
    if x_darkaudit_screen_metadata:
        try:
            from urllib.parse import unquote
            metadata = json.loads(unquote(x_darkaudit_screen_metadata))
        except (ValueError, TypeError):
            raise HTTPException(400, "화면 메타데이터가 잘못되었습니다.")
    with SessionLocal() as session:
        try:
            audit = get_audit(session, audit_id)
        except KeyError:
            raise HTTPException(404, "Audit not found")
        run = next_run(session, audit.id, "uploaded screenshots")
        target = UPLOAD_DIR / audit_id / f"run-{run.version}"
        target.mkdir(parents=True, exist_ok=True)
        for index, upload in enumerate(files, 1):
            content = await upload.read()
            if len(content) > 10 * 1024 * 1024:
                raise HTTPException(413, "이미지는 개당 10MB까지 업로드할 수 있습니다.")
            suffix = Path(upload.filename or "screen.png").suffix.lower()
            if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
                raise HTTPException(415, "PNG, JPG, WEBP 이미지만 지원합니다.")
            path = target / f"{index:02d}{suffix}"
            path.write_bytes(content)
            label = (
                flow_steps[index - 1] if index <= len(flow_steps)
                else metadata[index - 1].get("flowStep") if index <= len(metadata)
                else f"화면 {index}"
            )
            run.screens.append(Screen(
                flow_type=FlowType.join, screen_index=index, flow_step=label,
                image_path=public_image_path(path),
            ))
        session.commit()
        return to_audit_dto(session, audit, rules_by_id())


@app.post("/api/v1/audits/{audit_id}/analyze", response_model=JobDto, status_code=202)
def analyze(audit_id: str, background: BackgroundTasks) -> JobDto:
    with SessionLocal() as session:
        try:
            audit = get_audit(session, audit_id)
        except KeyError:
            raise HTTPException(404, "Audit not found")
        run = audit.runs[-1] if audit.runs else None
        if run is None or not run.screens:
            raise HTTPException(409, "분석할 화면을 먼저 업로드해주세요.")
        if run.status not in {RunStatus.PENDING, RunStatus.FAILED}:
            raise HTTPException(409, "이미 분석 중이거나 완료된 run입니다.")
        local_paths = [DATA_DIR / screen.image_path.removeprefix("/artifacts/") for screen in run.screens]
        job = create_job(audit_id, run.id)
        background.add_task(analyze_uploaded_screens, job.jobId, run.id, local_paths)
        return job


@app.post("/api/v1/audits/{audit_id}/capture", response_model=JobDto, status_code=202)
def capture(audit_id: str, payload: CaptureAuditRequest, background: BackgroundTasks) -> JobDto:
    if payload.mode == "smart" and not os.getenv("DARKAUDIT_COMPUTER_MODEL"):
        raise HTTPException(400, "smart 모드에는 DARKAUDIT_COMPUTER_MODEL 설정이 필요합니다.")
    try:
        UrlSafetyPolicy().validate(str(payload.url))
    except UnsafeUrlError as exc:
        raise HTTPException(400, str(exc))
    with SessionLocal() as session:
        try:
            audit = get_audit(session, audit_id)
        except KeyError:
            raise HTTPException(404, "Audit not found")
        run = next_run(session, audit.id, f"URL: {payload.url}")
        session.commit()
        job = create_job(audit_id, run.id)
        background.add_task(
            capture_and_analyze_url, job.jobId, run.id,
            audit_id=audit_id, url=str(payload.url), profiles=tuple(payload.profiles),
            mode=ScanMode(payload.mode), goal=payload.goal,
        )
        return job


@app.get("/api/v1/analysis-jobs/{job_id}", response_model=JobDto)
def analysis_job(job_id: str) -> JobDto:
    try:
        return get_job(job_id)
    except KeyError:
        raise HTTPException(404, "Job not found")


@app.patch("/api/v1/findings/{finding_id}")
def update_finding(finding_id: str, payload: FindingStatusRequest) -> dict[str, str]:
    try:
        pk = int(finding_id.rsplit("-", 1)[-1])
    except ValueError:
        raise HTTPException(404, "Finding not found")
    with SessionLocal() as session:
        finding = session.get(Finding, pk)
        if finding is None:
            raise HTTPException(404, "Finding not found")
        finding.status = FindingStatus.RESOLVED if payload.status == "resolved" else FindingStatus.OPEN
        session.commit()
    return {"id": finding_id, "status": payload.status}
