"""
DarkAudit Rule Base builder
---------------------------
dark_pattern_rules.yaml 을 검증하고 백엔드/AI 파이프라인에서 쓸 JSON으로 변환한다.

    python build_rules.py                 # 검증 + dark_pattern_rules.json 생성
    python build_rules.py --summary       # 검증 + 요약표 출력

Team B 소유. Team A는 생성된 JSON만 참조하면 되고, 규칙 수정은 YAML에서만 한다.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import yaml

HERE = Path(__file__).parent
SRC = HERE / "dark_pattern_rules.yaml"
OUT = HERE / "dark_pattern_rules.json"

REQUIRED_FIELDS = [
    "rule_id",
    "category",
    "official_name_ko",
    "official_definition",
    "detection_scope",
    "mvp_priority",
    "observable_features",
    "deterministic_checks",
    "semantic_checks",
    "required_evidence",
    "standalone_sufficient",
    "combination_amplifiers",
    "mitigating_checks",
    "label_unit",
    "related_required",
]

VALID_SCOPES = {"single_screen", "multi_screen", "dual_flow"}
VALID_PRIORITIES = {"P0", "P1", "P2"}
VALID_UNITS = {"element", "screen", "flow", "flow_pair"}


def validate(doc: dict) -> list[str]:
    errors: list[str] = []
    rules = doc.get("rules", [])
    categories = doc.get("categories", {})

    declared = doc.get("meta", {}).get("rule_count")
    if declared != len(rules):
        errors.append(f"meta.rule_count={declared} 이지만 실제 규칙 수는 {len(rules)}")

    seen_ids: set[str] = set()
    for rule in rules:
        rid = rule.get("rule_id", "<unknown>")

        for field in REQUIRED_FIELDS:
            if field not in rule:
                errors.append(f"{rid}: 필수 필드 '{field}' 누락")

        if rid in seen_ids:
            errors.append(f"{rid}: rule_id 중복")
        seen_ids.add(rid)

        if rule.get("category") not in categories:
            errors.append(f"{rid}: 정의되지 않은 category '{rule.get('category')}'")

        if rule.get("detection_scope") not in VALID_SCOPES:
            errors.append(f"{rid}: 잘못된 detection_scope '{rule.get('detection_scope')}'")

        if rule.get("mvp_priority") not in VALID_PRIORITIES:
            errors.append(f"{rid}: 잘못된 mvp_priority '{rule.get('mvp_priority')}'")

        # deterministic check 는 id/desc 를 반드시 갖는다 (Evidence 추적용)
        for check in rule.get("deterministic_checks", []):
            if not isinstance(check, dict) or "id" not in check or "desc" not in check:
                errors.append(f"{rid}: deterministic_checks 항목에 id/desc 누락")

        # semantic check 가 하나도 없으면 Multimodal LLM 검증 단계가 비게 된다
        if not rule.get("semantic_checks"):
            errors.append(f"{rid}: semantic_checks 가 비어 있음")

        if rule.get("label_unit") not in VALID_UNITS:
            errors.append(f"{rid}: 잘못된 label_unit '{rule.get('label_unit')}'")

        if not isinstance(rule.get("related_required"), bool):
            errors.append(f"{rid}: related_required 는 bool 이어야 함")

        # 관계가 없는 단위에 related 필수를 걸면 영우 라벨이 불가능해진다
        if rule.get("related_required") and rule.get("label_unit") != "element":
            errors.append(
                f"{rid}: related_required=true 는 label_unit=element 에서만 가능 "
                f"(현재 '{rule.get('label_unit')}')"
            )

        if not isinstance(rule.get("standalone_sufficient"), bool):
            errors.append(f"{rid}: standalone_sufficient 는 bool 이어야 함")

        # standalone_sufficient=false 인데 결합 대상이 없으면 영원히 승격 불가
        if rule.get("standalone_sufficient") is False and not rule.get("combination_amplifiers"):
            errors.append(
                f"{rid}: standalone_sufficient=false 인데 combination_amplifiers 가 비어 있음 "
                f"(HIGH 로 승격될 경로가 없다)"
            )

        for check in rule.get("mitigating_checks", []):
            if not isinstance(check, dict) or "id" not in check or "desc" not in check:
                errors.append(f"{rid}: mitigating_checks 항목에 id/desc 누락")

    # combination_amplifiers 참조 무결성 — 없는 rule_id 를 가리키면 severity 로직이 조용히 깨진다
    all_ids = {r.get("rule_id") for r in rules}
    for rule in rules:
        rid = rule.get("rule_id", "<unknown>")
        for ref in rule.get("combination_amplifiers", []):
            if ref not in all_ids:
                errors.append(f"{rid}: combination_amplifiers 가 존재하지 않는 '{ref}' 참조")
            if ref == rid:
                errors.append(f"{rid}: combination_amplifiers 가 자기 자신을 참조")

    # 범주별 선언 개수와 실제 개수 대조
    actual = Counter(r.get("category") for r in rules)
    for key, meta in categories.items():
        if meta.get("rule_count") != actual.get(key, 0):
            errors.append(
                f"category {key}: 선언 {meta.get('rule_count')} vs 실제 {actual.get(key, 0)}"
            )

    return errors


def summarize(doc: dict) -> None:
    rules = doc["rules"]
    cats = doc["categories"]

    print(f"\n총 {len(rules)}개 규칙\n")
    header = f"{'ID':<7} {'범주':<6} {'유형명':<18} {'범위':<13} {'우선':<4} {'단독':<4} {'라벨단위':<10} {'rel':<4} {'det':>3} {'sem':>3}"
    print(header)
    print("-" * len(header))

    for r in rules:
        print(
            f"{r['rule_id']:<7} "
            f"{cats[r['category']]['ko']:<6} "
            f"{r['official_name_ko']:<18} "
            f"{r['detection_scope']:<13} "
            f"{r['mvp_priority']:<4} "
            f"{'X' if r['standalone_sufficient'] else '결합':<4} "
            f"{r['label_unit']:<10} "
            f"{'필수' if r['related_required'] else '-':<4} "
            f"{len(r['deterministic_checks']):>3} "
            f"{len(r['semantic_checks']):>3}"
        )

    print()
    for label, key in [("우선순위", "mvp_priority"), ("탐지범위", "detection_scope")]:
        counts = Counter(r[key] for r in rules)
        parts = "  ".join(f"{k} {v}개" for k, v in sorted(counts.items()))
        print(f"{label}: {parts}")

    p0 = [r["rule_id"] for r in rules if r["mvp_priority"] == "P0"]
    print(f"\nMVP 대상(P0): {', '.join(p0)}")

    combo = [r["rule_id"] for r in rules if not r["standalone_sufficient"]]
    print(f"단독 HIGH 금지: {', '.join(combo)}  (결합 판정 필요)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", action="store_true", help="요약표 출력")
    args = parser.parse_args()

    doc = yaml.safe_load(SRC.read_text(encoding="utf-8"))

    errors = validate(doc)
    if errors:
        print("검증 실패:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    OUT.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"검증 통과 — {OUT.name} 생성 ({len(doc['rules'])}개 규칙)")

    if args.summary:
        summarize(doc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
