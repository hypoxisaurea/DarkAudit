"""Audit lifecycle and AI orchestration."""
import shutil
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from fastapi import UploadFile
from ai.pipeline.baseline import BaselineAuditPipeline, MVP_RULE_IDS
from ai.providers.factory import create_provider
from ai.rules.rule_loader import RuleLoader
from ai.schemas.audit_schema import AuditScreen, LLMAuditRequest
from backend.finding_mapper import to_finding_dto
from backend.schemas import AuditDto, CreateAuditRequest, JobDto, ScreenDto
from backend.storage import STORE

UPLOAD_ROOT = Path("data/uploads")
LOGGER = logging.getLogger(__name__)

def create_audit(request: CreateAuditRequest) -> AuditDto:
    audit = AuditDto(id=f"audit-{uuid.uuid4().hex}", name=request.name, platform=request.platform,
                     status="draft", updatedAt=datetime.now(timezone.utc), screens=[], findings=[])
    with STORE.lock: STORE.audits[audit.id] = audit
    return audit

def save_screens(audit_id: str, files: list[UploadFile], screen_ids: list[str], flow_steps: list[str]) -> AuditDto:
    if len(files) != len(screen_ids) or len(files) != len(flow_steps) or not 1 <= len(files) <= 5:
        raise ValueError("files, screen_ids and flow_steps must contain 1 to 5 matching items")
    audit = STORE.audits[audit_id]
    target = UPLOAD_ROOT / audit_id
    target.mkdir(parents=True, exist_ok=True)
    screens = []
    for index, (upload, screen_id, step) in enumerate(zip(files, screen_ids, flow_steps), 1):
        suffix = Path(upload.filename or "screen.png").suffix.lower() or ".png"
        path = target / f"{index:02d}-{screen_id}{suffix}"
        with path.open("wb") as output: shutil.copyfileobj(upload.file, output)
        screens.append(ScreenDto(id=screen_id, order=index, flowStep=step,
                                 imageUrl=f"/uploads/{audit_id}/{path.name}", findingCount=0))
    audit.screens, audit.updatedAt = screens, datetime.now(timezone.utc)
    return audit

def create_job(audit_id: str) -> JobDto:
    if not STORE.audits[audit_id].screens: raise ValueError("Upload screens before analysis")
    job = JobDto(jobId=f"job-{uuid.uuid4().hex}", auditId=audit_id, status="queued", progress=5)
    with STORE.lock:
        STORE.jobs[job.jobId] = job
        STORE.audits[audit_id].status = "queued"
    return job

def run_analysis(job_id: str) -> None:
    job = STORE.jobs[job_id]
    audit = STORE.audits[job.auditId]
    try:
        job.status, job.progress, audit.status = "analyzing", 35, "analyzing"
        request = LLMAuditRequest(audit.id, tuple(
            AuditScreen(screen.id, screen.flowStep, UPLOAD_ROOT / audit.id / Path(screen.imageUrl).name)
            for screen in sorted(audit.screens, key=lambda item: item.order)))
        result = BaselineAuditPipeline(create_provider()).analyze(request)
        rules = {rule["rule_id"]: rule for rule in RuleLoader().rules(rule_ids=MVP_RULE_IDS)}
        audit.findings = [to_finding_dto(item, rules) for item in result.detections]
        for screen in audit.screens:
            screen.findingCount = sum(screen.id in finding.screenIds for finding in audit.findings)
        job.status, job.progress, audit.status = "completed", 100, "completed"
    except Exception:
        LOGGER.exception("Audit analysis failed: job_id=%s audit_id=%s", job_id, audit.id)
        job.status, job.progress, audit.status = "failed", 100, "failed"
    finally:
        audit.updatedAt = datetime.now(timezone.utc)
