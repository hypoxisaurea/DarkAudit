"""Application service joining the HTTP API to the screenshot and URL AI pipelines."""

from __future__ import annotations

import os
import threading
from pathlib import Path

from sqlalchemy import select

from ai.browser.explorer import HybridWebExplorer
from ai.browser.models import CaptureArtifact, ScanMode
from ai.browser.playwright_driver import PlaywrightSessionFactory
from ai.pipeline.baseline import MVP_RULE_IDS, BaselineAuditPipeline
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
FIGMA_DIR = DATA_DIR / "figma"

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
        analyze_run_screens(job_id, run_id, local_paths)
    except Exception as exc:  # background jobs must expose failures to the polling client
        _fail_job(job_id, run_id, exc)


def analyze_run_screens(job_id: str, run_id: int, local_paths: list[Path]) -> None:
    """LLM 분석 + DB 저장. 업로드/Figma 등 모든 수집기가 이 함수를 공유한다.

    수집기별로 진행률 갱신(_mark_running)을 먼저 마친 뒤 호출해야 하며,
    예외 처리는 호출부 책임이다(각 수집기가 자기 맥락으로 _fail_job 을 부른다).
    """
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

            _store_output(session, run, result.analysis, rule_findings, element_lookup)
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
                for element in artifact.dom_elements
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
        for element in artifact.dom_elements:
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
    # LLM 이 검증하기 전에 Rule Engine 이 같은 rule_id·화면을 이미 찾았다면
    # base_severity/severity 는 Rule Engine 값을 최종으로 쓴다 (rule_ai_contract.md).
    rule_by_key = {_rule_finding_key(finding): finding for finding in (rule_findings or [])}

    for detection in output.detections:
        referenced = [screens[screen_id] for screen_id in detection.where.screen_ids]
        indices = [screen.screen_index for screen in referenced]
        label_unit = rules[detection.rule_id]["label_unit"]
        matched = rule_by_key.pop((detection.rule_id, tuple(sorted(indices))), None)

        primary = None
        if label_unit == "element":
            primary = element_lookup.get(matched.primary_id) if matched and matched.primary_id else None
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
            base_severity=Severity(matched.base_severity) if matched else Severity(detection.severity.value),
            severity=Severity(matched.severity) if matched else Severity(detection.severity.value),
            combination_with=list(matched.combination_with) if matched else [],
            mitigated_by=list(matched.mitigated_by) if matched else [],
            mitigated=matched.mitigated if matched else False,
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
            triggered_checks=list(matched.triggered_checks) if matched else [],
            measurements=matched.measurements if matched else None,
        )
        if matched:
            for related_id in matched.related_ids:
                related_element = element_lookup.get(related_id)
                if related_element is not None:
                    finding.related.append(FindingRelatedElement(element=related_element))
        run.findings.append(finding)

    # LLM 은 놓쳤지만 Rule Engine 이 단독으로 찾은 결과도 그대로 남긴다.
    for finding_ in rule_by_key.values():
        run.findings.append(_rule_only_finding(finding_, rules, element_lookup))

    run.status = RunStatus.DONE


def _rule_only_finding(
    finding: ScoredFinding, rules: dict, element_lookup: dict[str, Element]
) -> Finding:
    indices = [finding.screen_index] if finding.screen_index is not None else finding.screen_indices
    rule = rules.get(finding.rule_id, {})
    primary = element_lookup.get(finding.primary_id) if finding.primary_id else None

    row = Finding(
        rule_id=finding.rule_id,
        label_unit=finding.label_unit,
        fingerprint=make_fingerprint(
            finding.rule_id,
            screen_index=indices[0] if indices else None,
            bbox=primary.bbox if primary else None,
            text=primary.text if primary else None,
            label_unit=finding.label_unit,
        ),
        primary_element=primary,
        screen_indices=indices,
        base_severity=Severity(finding.base_severity),
        severity=Severity(finding.severity),
        combination_with=list(finding.combination_with),
        mitigated_by=list(finding.mitigated_by),
        mitigated=finding.mitigated,
        status=FindingStatus.OPEN,
        confidence=None,
    )
    row.evidence = Evidence(
        where_text=f"screens={indices}" if indices else None,
        what_text=primary.text if primary else None,
        observation=None,
        rule_ref=finding.rule_id,
        why_text=rule.get("official_definition"),
        fix_text=rule.get("fix_template"),
        triggered_checks=list(finding.triggered_checks),
        measurements=finding.measurements,
    )
    for related_id in finding.related_ids:
        related_element = element_lookup.get(related_id)
        if related_element is not None:
            row.related.append(FindingRelatedElement(element=related_element))
    return row


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

