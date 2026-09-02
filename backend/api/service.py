"""Application service joining the HTTP API to the screenshot and URL AI pipelines."""

from __future__ import annotations

import os
import threading
from pathlib import Path

from sqlalchemy import select

from ai.browser.explorer import HybridWebExplorer
from ai.browser.models import ScanMode
from ai.browser.playwright_driver import PlaywrightSessionFactory
from ai.pipeline.baseline import BaselineAuditPipeline
from ai.pipeline.web_audit import URLAuditPipeline, URLCapturePipeline, select_analysis_artifacts
from ai.providers import create_provider
from ai.providers.computer_use import OpenAIComputerUseAgent
from ai.rules.rule_loader import RuleLoader
from ai.schemas.audit_schema import AuditScreen, LLMAuditOutput, LLMAuditRequest
from backend.app.fingerprint import make as make_fingerprint
from backend.app.models import (
    AuditRun,
    Element,
    Evidence,
    Finding,
    FindingStatus,
    FlowType,
    RunStatus,
    Screen,
    Severity,
)
from backend.app.regression import compare

from .schemas import JobDto
from .store import SessionLocal, new_id

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CAPTURE_DIR = DATA_DIR / "captures"

_jobs: dict[str, JobDto] = {}
_jobs_lock = threading.Lock()


def rules_by_id() -> dict[str, dict]:
    return {rule["rule_id"]: rule for rule in RuleLoader().rules()}


def create_job(audit_id: str, run_id: int) -> JobDto:
    job = JobDto(
        jobId=new_id("job"), auditId=audit_id, runId=f"run-{run_id}",
        status="queued", progress=5,
    )
    with _jobs_lock:
        _jobs[job.jobId] = job
    return job


def get_job(job_id: str) -> JobDto:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        return job.model_copy(deep=True)


def _update_job(job_id: str, **changes: object) -> None:
    with _jobs_lock:
        job = _jobs[job_id]
        for key, value in changes.items():
            setattr(job, key, value)


def next_run(session, audit_id: int, note: str | None = None) -> AuditRun:
    latest = session.scalar(
        select(AuditRun.version)
        .where(AuditRun.audit_id == audit_id)
        .order_by(AuditRun.version.desc())
        .limit(1)
    )
    run = AuditRun(audit_id=audit_id, version=(latest or 0) + 1, status=RunStatus.PENDING, note=note)
    session.add(run)
    session.flush()
    return run


def public_image_path(path: Path) -> str:
    resolved = path.resolve()
    relative = resolved.relative_to(DATA_DIR.resolve())
    return "/artifacts/" + relative.as_posix()


def analyze_uploaded_screens(job_id: str, run_id: int, local_paths: list[Path]) -> None:
    try:
        _mark_running(job_id, run_id, 20)
        with SessionLocal() as session:
            run = session.get(AuditRun, run_id)
            if run is None:
                raise ValueError("Analysis run no longer exists")
            request = LLMAuditRequest(
                f"audit-{run.audit_id}",
                tuple(
                    AuditScreen(f"screen-{screen.screen_index:02d}", screen.flow_step or f"화면 {screen.screen_index}", path)
                    for screen, path in zip(run.screens, local_paths, strict=True)
                ),
            )
            output = BaselineAuditPipeline(create_provider()).analyze(request)
            _update_job(job_id, progress=80)
            _store_output(session, run, output)
            _apply_regression(session, run)
            session.commit()
        _update_job(job_id, status="completed", progress=100)
    except Exception as exc:  # background jobs must expose failures to the polling client
        _fail_job(job_id, run_id, exc)


def capture_and_analyze_url(
    job_id: str,
    run_id: int,
    *,
    audit_id: str,
    url: str,
    profiles: tuple[str, ...],
    mode: ScanMode,
    goal: str | None,
) -> None:
    try:
        _mark_running(job_id, run_id, 12)
        computer_agent = None
        if mode is ScanMode.SMART:
            computer_agent = OpenAIComputerUseAgent(os.environ["DARKAUDIT_COMPUTER_MODEL"])
        explorer = HybridWebExplorer(
            PlaywrightSessionFactory(CAPTURE_DIR), computer_agent=computer_agent
        )
        pipeline = URLAuditPipeline(
            URLCapturePipeline(explorer), BaselineAuditPipeline(create_provider())
        )
        result = pipeline.run(
            audit_id=audit_id, url=url, profiles=profiles, mode=mode, goal=goal
        )
        _update_job(job_id, progress=78)
        selected = select_analysis_artifacts(result.capture.artifacts, 5)
        with SessionLocal() as session:
            run = session.get(AuditRun, run_id)
            if run is None:
                raise ValueError("Capture run no longer exists")
            for index, artifact in enumerate(selected, 1):
                run.screens.append(
                    Screen(
                        flow_type=FlowType.join,
                        screen_index=index,
                        flow_step=artifact.flow_step,
                        image_path=public_image_path(artifact.image_path),
                        viewport_w=artifact.viewport_width,
                        viewport_h=artifact.viewport_height,
                    )
                )
            _store_output(session, run, result.analysis)
            _apply_regression(session, run)
            session.commit()
        _update_job(job_id, status="completed", progress=100)
    except Exception as exc:
        _fail_job(job_id, run_id, exc)


def _mark_running(job_id: str, run_id: int, progress: float) -> None:
    with SessionLocal() as session:
        run = session.get(AuditRun, run_id)
        if run is None:
            raise ValueError("Analysis run no longer exists")
        run.status = RunStatus.RUNNING
        session.commit()
    _update_job(job_id, status="analyzing", progress=progress)


def _fail_job(job_id: str, run_id: int, exc: Exception) -> None:
    with SessionLocal() as session:
        run = session.get(AuditRun, run_id)
        if run is not None:
            run.status = RunStatus.FAILED
            run.note = str(exc)[:1000]
            session.commit()
    _update_job(job_id, status="failed", error=str(exc), progress=100)


def _store_output(session, run: AuditRun, output: LLMAuditOutput) -> None:
    ordered_screens = sorted(run.screens, key=lambda screen: screen.screen_index)
    if len(ordered_screens) != len(output.screens):
        raise ValueError("분석 결과의 화면 수가 저장된 화면 수와 다릅니다.")
    screens = {
        reference.screen_id: screen
        for reference, screen in zip(output.screens, ordered_screens, strict=True)
    }
    rules = rules_by_id()
    for detection in output.detections:
        referenced = [screens[screen_id] for screen_id in detection.where.screen_ids]
        indices = [screen.screen_index for screen in referenced]
        label_unit = rules[detection.rule_id]["label_unit"]
        primary = None
        if label_unit == "element":
            primary = Element(
                screen=referenced[0],
                element_type="vision",
                text=detection.where.element,
                bbox_x=0.0,
                bbox_y=0.0,
                bbox_w=0.0,
                bbox_h=0.0,
                source="vision",
                confidence=detection.confidence,
            )
            session.add(primary)
            session.flush()

        finding = Finding(
            rule_id=detection.rule_id,
            label_unit=label_unit,
            fingerprint=make_fingerprint(
                detection.rule_id,
                screen_index=indices[0] if indices else None,
                text=detection.where.element,
                label_unit=label_unit,
            ),
            primary_element=primary,
            screen_indices=indices,
            base_severity=Severity(detection.severity.value),
            severity=Severity(detection.severity.value),
            combination_with=[],
            mitigated_by=[],
            mitigated=False,
            status=FindingStatus.OPEN,
            confidence=detection.confidence,
        )
        finding.evidence = Evidence(
            where_text=detection.where.location,
            what_text=detection.what,
            observation=detection.observation,
            rule_ref=detection.rule_id,
            why_text=detection.why,
            fix_text=detection.fix,
            triggered_checks=[],
        )
        run.findings.append(finding)
    run.status = RunStatus.DONE


def _apply_regression(session, run: AuditRun) -> None:
    previous = session.scalar(
        select(AuditRun)
        .where(
            AuditRun.audit_id == run.audit_id,
            AuditRun.version < run.version,
            AuditRun.status == RunStatus.DONE,
        )
        .order_by(AuditRun.version.desc())
    )
    if previous is not None:
        compare(session, run.audit_id, previous.version, run.version)

