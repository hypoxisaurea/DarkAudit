# Rule Base ↔ AI Interface v1

B는 `rules/dark_pattern_rules.yaml`의 규제 지식과 Rule ID를 소유하고, A는 화면 관찰 결과와 구조화 출력을 소유한다.

## B → A

필수 필드: `rule_id`, `official_name_ko`, `official_definition`, `detection_scope`, `standalone_sufficient`, `observable_features`, `deterministic_checks`, `semantic_checks`, `mitigating_checks`, `combination_amplifiers`, `required_evidence`, `fix_template`.

## A → B/API

필수 필드: `screen_id`, `flow_step`, `detections[].risk_type`, `risk_name`, `where`, `what`, `observation`, `rule_id`, `why`, `severity`, `confidence`, `fix`.

정식 계약은 `ai/schemas/audit_output.schema.json`이다. API·DB는 JSON Schema v1을 기준으로 구현하며 임의 필드를 추가하지 않는다. 변경 시 Schema 버전과 Golden Test를 함께 갱신한다.

고정 매핑: `DA-04 → PRESELECTED_OPTION`, `DA-03 → VISUAL_HIERARCHY_DISTORTION`, `DA-12 → EMOTIONAL_LANGUAGE`, `DA-15 → SEQUENTIAL_PRICE_DISCLOSURE`.
