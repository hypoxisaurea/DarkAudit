# Rule Base ↔ AI Interface v1.1

B는 `rules/dark_pattern_rules.yaml`의 규제 지식과 Rule ID를 소유하고, A는 화면 관찰 결과와 구조화 출력을 소유한다.

## B → A

필수 필드: `rule_id`, `official_name_ko`, `official_definition`, `detection_scope`, `standalone_sufficient`, `observable_features`, `deterministic_checks`, `semantic_checks`, `mitigating_checks`, `combination_amplifiers`, `required_evidence`, `fix_template`.

## A → B/API

필수 필드: `screen_id`, `flow_step`, `detections[].risk_type`, `risk_name`, `where`, `bbox`, `related_elements`, `what`, `observation`, `rule_id`, `why`, `severity`, `confidence`, `fix`.

정식 계약은 `ai/schemas/audit_output.schema.json`이다. API·DB는 JSON Schema v1.1을 기준으로 구현하며 임의 필드를 추가하지 않는다. 변경 시 Schema 버전과 Golden Test를 함께 갱신한다.

- `bbox`: 주 근거 요소의 `[x, y, width, height]` 화면 정규화 좌표(0~1). DA-15에서는 마지막 Evidence 화면의 현재 가격·비용 요소를 가리킨다.
- `related_elements[]`: 상대 근거의 `screen_id`, `element`, 정규화 `bbox`. DA-03은 같은 화면의 대립 선택지를 최소 1개 포함해야 한다.
- `severity`: AI의 최종 판정이 아니라 Rule Base의 `base_severity`. 결합 승격·완화 전 값이므로 DA-03·DA-04·DA-15는 `HIGH`, DA-12는 `REVIEW`다.
- Multi-label: 같은 주 요소에 서로 다른 Rule Detection을 각각 출력할 수 있다. 같은 요소·같은 Rule 중복만 금지한다.
- DA-15: `flow_step`의 device profile 접두사가 같은 화면끼리만 비교한다. `desktop`, `mobile`, `iphone`, 접두사가 없는 `unspecified`는 각각 독립 프로필이다.

고정 매핑: `DA-04 → PRESELECTED_OPTION`, `DA-03 → VISUAL_HIERARCHY_DISTORTION`, `DA-12 → EMOTIONAL_LANGUAGE`, `DA-15 → SEQUENTIAL_PRICE_DISCLOSURE`.
