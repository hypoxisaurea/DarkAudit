"""Application service joining the HTTP API to the screenshot and URL AI pipelines."""

from __future__ import annotations

import os
import inspect
import threading
from pathlib import Path

from sqlalchemy import select

from ai.browser.explorer import HybridWebExplorer
from ai.browser.models import CaptureArtifact, ScanMode
from ai.browser.playwright_driver import PlaywrightSessionFactory
from ai.pipeline.baseline import MVP_RULE_IDS, BaselineAuditPipeline
from ai.pipeline.web_audit import URLCapturePipeline, select_analysis_artifacts
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
    FindingRelatedElement,
    FindingStatus,
    FlowType,
    RunStatus,
    Screen,
    Severity,
)
from backend.app.regression import compare
from backend.app.rule_engine import checks as _rule_engine_checks  # noqa: F401  — 데코레이터 등록을 위해 필요
from backend.app.rule_engine.core import Element as RuleElement
from backend.app.rule_engine.core import Flow as RuleFlow
from backend.app.rule_engine.core import RuleBase
from backend.app.rule_engine.core import Screen as RuleScreen
from backend.app.rule_engine.core import run as run_rule_engine
from backend.app.rule_engine.severity import ScoredFinding, drop_incomplete
from backend.app.rule_engine.severity import merge as merge_rule_detections
from backend.app.rule_engine.severity import score as score_rule_findings

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
        capture = URLCapturePipeline(explorer).run(
            audit_id=audit_id, url=url, profiles=profiles, mode=mode, goal=goal
        )
        selected = select_analysis_artifacts(capture.artifacts, 5)
        with SessionLocal() as session:
            run = session.get(AuditRun, run_id)
            if run is None:
                raise ValueError("Capture run no longer exists")
            screens: list[Screen] = []
            for index, artifact in enumerate(selected, 1):
                screen = Screen(
                    flow_type=FlowType.join,
                    screen_index=index,
                    flow_step=artifact.flow_step,
                    image_path=public_image_path(artifact.image_path),
                    viewport_w=artifact.viewport_width,
                    viewport_h=artifact.viewport_height,
                )
                run.screens.append(screen)
                screens.append(screen)

            # URL 캡처만 DOM 을 갖고 있으므로 Rule Engine 은 이 경로에서만 돈다.
            element_lookup = _persist_dom_elements(session, screens, selected)
            rule_findings = _run_rule_engine(run.audit_id, screens, selected)

            request = LLMAuditRequest(
                audit_id,
                tuple(
                    AuditScreen(artifact.screen_id, artifact.flow_step, artifact.image_path)
                    for artifact in selected
                ),
            )
            candidates = _candidate_payload(rule_findings, screens, selected)
            pipeline = BaselineAuditPipeline(create_provider())
            analyze_parameters = inspect.signature(pipeline.analyze).parameters
            analysis = (
                pipeline.analyze(request, candidates)
                if "candidates" in analyze_parameters
                else pipeline.analyze(request)
            )
            _update_job(job_id, progress=78)

            _store_output(session, run, analysis, rule_findings, element_lookup)
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


def _build_rule_flow(
    audit_id: int, screens: list[Screen], artifacts: tuple[CaptureArtifact, ...]
) -> RuleFlow:
    rule_screens = [
        RuleScreen(
            screen.screen_index,
            [
                RuleElement(
                    element_id=element["element_id"],
                    element_type=element["element_type"],
                    text=element.get("text"),
                    bbox=element["bbox"],
                    state=element.get("state") or {},
                    style=element.get("computed_style") or {},
                )
                for element in getattr(artifact, "dom_elements", ())
            ],
        )
        for screen, artifact in zip(screens, artifacts, strict=True)
    ]
    return RuleFlow(flow_id=f"audit-{audit_id}", flow_type="join", sector=None, screens=rule_screens)


def _persist_dom_elements(
    session, screens: list[Screen], artifacts: tuple[CaptureArtifact, ...]
) -> dict[str, Element]:
    """캡처된 DOM 요소를 전부 저장한다 (models.py 설계 결정 #2).

    Finding 에 걸리지 않은 요소도 남겨야 임계값을 조정했을 때 재계산만으로
    결과를 갱신할 수 있다.
    """
    lookup: dict[str, Element] = {}
    for screen, artifact in zip(screens, artifacts, strict=True):
        for element in getattr(artifact, "dom_elements", ()):
            x, y, w, h = element["bbox"]
            row = Element(
                screen=screen,
                dom_id=element["element_id"],
                element_type=element.get("element_type"),
                text=element.get("text"),
                bbox_x=x, bbox_y=y, bbox_w=w, bbox_h=h,
                state=element.get("state") or {},
                computed_style=element.get("computed_style") or {},
                source="dom",
            )
            session.add(row)
            lookup[element["element_id"]] = row
    session.flush()
    return lookup


def _run_rule_engine(
    audit_id: int, screens: list[Screen], artifacts: tuple[CaptureArtifact, ...]
) -> list[ScoredFinding]:
    rb = RuleBase()
    flow = _build_rule_flow(audit_id, screens, artifacts)
    detections = run_rule_engine(flow, rb, only=MVP_RULE_IDS)
    return score_rule_findings(drop_incomplete(merge_rule_detections(detections, rb), rb), rb)


def _rule_finding_key(finding: ScoredFinding) -> tuple[str, tuple[int, ...]]:
    indices = [finding.screen_index] if finding.screen_index is not None else finding.screen_indices
    return (finding.rule_id, tuple(sorted(indices)))


def _candidate_payload(
    findings: list[ScoredFinding],
    screens: list[Screen],
    artifacts: tuple[CaptureArtifact, ...],
) -> list[dict]:
    """Make deterministic evidence explicit without presenting it as a verdict."""
    screen_ids = {
        screen.screen_index: artifact.screen_id
        for screen, artifact in zip(screens, artifacts, strict=True)
    }
    elements = {
        element["element_id"]: {
            "element_id": element["element_id"],
            "element_type": element.get("element_type"),
            "text": element.get("text"),
            "bbox": element.get("bbox"),
            "state": element.get("state") or {},
            "computed_style": element.get("computed_style") or {},
        }
        for artifact in artifacts
        for element in getattr(artifact, "dom_elements", ())
    }
    return [
        {
            "rule_id": finding.rule_id,
            "screen_ids": [screen_ids[index] for index in (
                [finding.screen_index] if finding.screen_index is not None
                else finding.screen_indices
            ) if index in screen_ids],
            "primary_element_id": finding.primary_id,
            "related_element_ids": list(finding.related_ids),
            "primary_element": elements.get(finding.primary_id),
            "related_elements": [
                elements[element_id]
                for element_id in finding.related_ids
                if element_id in elements
            ],
            "triggered_checks": list(finding.triggered_checks),
            "measurements": finding.measurements,
        }
        for finding in findings
    ]


def _store_output(
    session,
    run: AuditRun,
    output: LLMAuditOutput,
    rule_findings: list[ScoredFinding] | None = None,
    element_lookup: dict[str, Element] | None = None,
) -> None:
    ordered_screens = sorted(run.screens, key=lambda screen: screen.screen_index)
    if len(ordered_screens) != len(output.screens):
        raise ValueError("분석 결과의 화면 수가 저장된 화면 수와 다릅니다.")
    screens = {
        reference.screen_id: screen
        for reference, screen in zip(output.screens, ordered_screens, strict=True)
    }
    rules = rules_by_id()
    element_lookup = element_lookup or {}
    # Match deterministic evidence to the model's verified findings. Unmatched
    # candidates are deliberately not persisted as findings.
    candidate_pool: dict[tuple[str, tuple[int, ...]], list[ScoredFinding]] = {}
    for candidate in rule_findings or []:
        candidate_pool.setdefault(_rule_finding_key(candidate), []).append(candidate)

    verified = []
    for detection in output.detections:
        referenced = [screens[screen_id] for screen_id in detection.where.screen_ids]
        indices = [screen.screen_index for screen in referenced]
        candidates = candidate_pool.get((detection.rule_id, tuple(sorted(indices)))) or []
        matched = candidates.pop(0) if candidates else ScoredFinding(
            rule_id=detection.rule_id,
            label_unit=rules[detection.rule_id]["label_unit"],
            screen_index=indices[0] if len(indices) == 1 else None,
            primary_id=None,
            screen_indices=indices if len(indices) > 1 else [],
        )
        verified.append((detection, referenced, indices, matched))

    score_rule_findings([item[3] for item in verified], RuleBase())

    for detection, referenced, indices, matched in verified:
        label_unit = matched.label_unit

        primary = None
        if label_unit == "element":
            primary = element_lookup.get(matched.primary_id) if matched.primary_id else None
            if primary is None:
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
            base_severity=Severity(matched.base_severity),
            severity=Severity(matched.severity),
            combination_with=list(matched.combination_with),
            mitigated_by=list(matched.mitigated_by),
            mitigated=matched.mitigated,
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
            triggered_checks=list(matched.triggered_checks),
            measurements=matched.measurements or None,
        )
        for related_id in matched.related_ids:
            related_element = element_lookup.get(related_id)
            if related_element is not None:
                finding.related.append(FindingRelatedElement(element=related_element))
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

