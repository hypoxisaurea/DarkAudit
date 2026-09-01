"""
Regression Audit
----------------
같은 Audit 의 두 회차를 비교해 위험이 실제로 해소됐는지 판정한다.

fingerprint 를 키로 양쪽 Finding 을 맞춰본다.

    이전에만 있음   → RESOLVED   (해소)
    양쪽에 있음     → OPEN       (미해결). severity 가 낮아졌으면 개선으로 별도 표시
    이번에만 있음   → OPEN       (신규). 이전에 RESOLVED 였다면 REGRESSED

REGRESSED 판정에는 v1 뿐 아니라 그 이전 회차 전체를 봐야 한다.
v1 에서 해결한 문제가 v3 에서 다시 나타나는 경우를 잡기 위해서다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AuditRun, Finding, FindingStatus, Severity

SEVERITY_ORDER = {Severity.LOW: 0, Severity.REVIEW: 1, Severity.HIGH: 2}


@dataclass
class Change:
    fingerprint: str
    rule_id: str
    before: Severity | None = None
    after: Severity | None = None

    @property
    def improved(self) -> bool:
        if self.before is None or self.after is None:
            return False
        return SEVERITY_ORDER[self.after] < SEVERITY_ORDER[self.before]


@dataclass
class RegressionReport:
    audit_id: int
    from_version: int
    to_version: int

    resolved: list[Change] = field(default_factory=list)     # 해소됨
    persisted: list[Change] = field(default_factory=list)    # 남아 있음
    improved: list[Change] = field(default_factory=list)     # 남아 있으나 위험도 하락
    new: list[Change] = field(default_factory=list)          # 신규
    regressed: list[Change] = field(default_factory=list)    # 재발

    @property
    def resolved_ratio(self) -> float:
        """
        Resolved Finding Ratio — 기획서의 핵심 검증 지표.
        이전 회차 Finding 중 해소된 비율.
        """
        total = len(self.resolved) + len(self.persisted) + len(self.improved)
        return len(self.resolved) / total if total else 0.0

    def summary(self) -> dict:
        return {
            "audit_id": self.audit_id,
            "from": f"v{self.from_version}",
            "to": f"v{self.to_version}",
            "resolved": len(self.resolved),
            "improved": len(self.improved),
            "persisted": len(self.persisted),
            "new": len(self.new),
            "regressed": len(self.regressed),
            "resolved_ratio": round(self.resolved_ratio, 3),
        }


def _findings(session: Session, run_id: int) -> dict[str, Finding]:
    rows = session.scalars(select(Finding).where(Finding.run_id == run_id)).all()
    return {f.fingerprint: f for f in rows}


def _previously_resolved(session: Session, audit_id: int, before_version: int) -> set[str]:
    """이전 회차들에서 한 번이라도 RESOLVED 로 기록된 fingerprint."""
    runs = session.scalars(
        select(AuditRun).where(
            AuditRun.audit_id == audit_id, AuditRun.version < before_version
        )
    ).all()
    out: set[str] = set()
    for r in runs:
        for f in r.findings:
            if f.status == FindingStatus.RESOLVED:
                out.add(f.fingerprint)
    return out


def compare(session: Session, audit_id: int, from_version: int, to_version: int) -> RegressionReport:
    prev_run = session.scalar(
        select(AuditRun).where(
            AuditRun.audit_id == audit_id, AuditRun.version == from_version
        )
    )
    curr_run = session.scalar(
        select(AuditRun).where(
            AuditRun.audit_id == audit_id, AuditRun.version == to_version
        )
    )
    if prev_run is None or curr_run is None:
        raise ValueError(f"회차를 찾을 수 없다: v{from_version} 또는 v{to_version}")

    prev = _findings(session, prev_run.id)
    curr = _findings(session, curr_run.id)
    ever_resolved = _previously_resolved(session, audit_id, to_version)

    report = RegressionReport(audit_id, from_version, to_version)

    for fp, pf in prev.items():
        if fp in curr:
            cf = curr[fp]
            ch = Change(fp, pf.rule_id, pf.severity, cf.severity)
            (report.improved if ch.improved else report.persisted).append(ch)
        else:
            report.resolved.append(Change(fp, pf.rule_id, before=pf.severity))

    for fp, cf in curr.items():
        if fp in prev:
            continue
        ch = Change(fp, cf.rule_id, after=cf.severity)
        if fp in ever_resolved:
            report.regressed.append(ch)
            cf.status = FindingStatus.REGRESSED
        else:
            report.new.append(ch)

    # 이전 회차 Finding 의 상태를 갱신한다.
    # 다음 비교에서 재발 여부를 판단하려면 이 기록이 남아 있어야 한다.
    resolved_fps = {c.fingerprint for c in report.resolved}
    for fp, pf in prev.items():
        pf.status = FindingStatus.RESOLVED if fp in resolved_fps else FindingStatus.OPEN

    session.flush()
    return report
