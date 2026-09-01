"""
Rule Engine 평가
---------------
추출한 UI 표현에 Rule Engine 을 돌리고 정답 라벨과 대조한다.

주의: 여기서 나오는 수치는 **deterministic check 단독 성능**이다.
Multimodal LLM 의 semantic 검증이 붙기 전 값이므로, 의미 판단이 필요한 유형은
낮게 나오는 것이 정상이다. 오히려 이 값이 높으면 semantic 단계가 불필요하다는
뜻이므로 파이프라인 설계를 재검토해야 한다.

    python eval_rule_engine.py
"""

from __future__ import annotations

import collections
import json
from pathlib import Path

from app.rule_engine import checks  # noqa: F401  — 데코레이터 등록을 위해 필요
from app.rule_engine.core import RuleBase, audit_coverage, load_flow, run
from app.rule_engine.severity import drop_incomplete, merge, score

ROOT = Path(__file__).resolve().parents[1] / "data" / "synthetic"
UI = ROOT / "ui"
LABELS = ROOT / "labels"

# 현재 구현한 유형만 평가 대상으로 삼는다.
TARGET = {"DA-03", "DA-04", "DA-07", "DA-12", "DA-13", "DA-15"}


def gold_of(doc: dict) -> set[tuple[str, int | None]]:
    """정답 라벨을 (rule_id, screen_index) 집합으로. flow 단위는 screen=None."""
    out = set()
    for l in doc["labels"]:
        if l["rule_id"] not in TARGET:
            continue
        if l["label_unit"] == "element":
            out.add((l["rule_id"], l["primary"]["screen_index"]))
        else:
            out.add((l["rule_id"], None))
    return out


def pred_of(findings) -> set[tuple[str, int | None]]:
    return {
        (f.rule_id, f.screen_index if f.label_unit == "element" else None)
        for f in findings
        if f.rule_id in TARGET
    }


def main() -> None:
    rb = RuleBase()

    cov = audit_coverage(rb)
    print(f"체크 구현 현황: 선언 {cov['declared']} 중 {cov['implemented']} 구현")
    target_missing = [m for m in cov["missing"] if m.split(".")[0] in TARGET]
    if target_missing:
        print(f"  P0 유형 미구현: {', '.join(target_missing)}")
    print()

    tp = collections.Counter()
    fp = collections.Counter()
    fn = collections.Counter()
    rows = []

    for ui_path in sorted(UI.glob("*.json")):
        doc = json.loads(ui_path.read_text(encoding="utf-8"))
        flow = load_flow(doc)

        label_path = LABELS / f"{flow.flow_id}.json"
        if not label_path.exists():
            continue
        gold = gold_of(json.loads(label_path.read_text(encoding="utf-8")))

        dets = run(flow, rb, only=TARGET)
        findings = score(drop_incomplete(merge(dets, rb), rb), rb)
        pred = pred_of(findings)

        for k in pred & gold:
            tp[k[0]] += 1
        for k in pred - gold:
            fp[k[0]] += 1
        for k in gold - pred:
            fn[k[0]] += 1

        rows.append((flow.flow_id, len(gold), len(pred), len(pred & gold),
                     len(pred - gold), len(gold - pred)))

    print(f"{'flow':<18}{'정답':>4}{'탐지':>5}{'TP':>4}{'FP':>4}{'FN':>4}")
    print("-" * 40)
    for r in rows:
        print(f"{r[0]:<18}{r[1]:>4}{r[2]:>5}{r[3]:>4}{r[4]:>4}{r[5]:>4}")

    print(f"\n{'rule':<8}{'TP':>4}{'FP':>4}{'FN':>4}{'P':>7}{'R':>7}{'F1':>7}")
    print("-" * 40)
    f1s = []
    for rid in sorted(TARGET):
        t, f_, n = tp[rid], fp[rid], fn[rid]
        p = t / (t + f_) if t + f_ else 0.0
        r = t / (t + n) if t + n else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        f1s.append(f1)
        print(f"{rid:<8}{t:>4}{f_:>4}{n:>4}{p:>7.2f}{r:>7.2f}{f1:>7.2f}")

    T, F, N = sum(tp.values()), sum(fp.values()), sum(fn.values())
    P = T / (T + F) if T + F else 0.0
    R = T / (T + N) if T + N else 0.0
    print("-" * 40)
    print(f"{'micro':<8}{T:>4}{F:>4}{N:>4}{P:>7.2f}{R:>7.2f}"
          f"{(2*P*R/(P+R) if P+R else 0):>7.2f}")
    print(f"{'macro F1':<8}{sum(f1s)/len(f1s):>29.2f}")


if __name__ == "__main__":
    main()
