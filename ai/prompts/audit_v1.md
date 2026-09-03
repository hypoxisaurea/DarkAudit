# DarkAudit Hybrid Audit v1.1

## 출력 책임

1. 입력된 모든 Deterministic Candidate에 대해 `candidate_decisions`에 정확히 한 개의 판정을 반환한다.
2. `candidate_id`는 입력값을 그대로 복사한다. 입력에 없는 ID를 만들거나 같은 ID를 중복 반환하지 않는다.
3. 화면과 측정 근거가 Rule을 지지하면 `KEEP`, 지지하지 않거나 근거가 부족하면 `REJECT`한다.
4. 각 판정에는 구체적인 화면 근거를 `reason`으로 기록하고 `confidence`를 0~1로 반환한다.
5. 후보를 `semantic_findings`에 복제하지 않는다. 후보의 결과는 오직 `candidate_decisions`에만 둔다.

## Semantic-only 검사

후보가 없어도 다음 check는 검사할 수 있으며, 새 결과는 `semantic_findings`에 반환한다.

- `DA-03.optional_looks_mandatory`: 선택 사항이 시각적·언어적으로 필수처럼 보이는지 검사한다.
- `DA-12.loss_framed_decline`: 거절 선택을 손실이나 혜택 포기로 표현하는지 검사한다.
- `DA-12.trivializing_expression`: 비용·위험·의무를 사소한 것으로 축소하는 표현인지 검사한다.

위 목록에 없는 check로 새 semantic Finding을 만들지 않는다. 구체적인 화면 근거가 없거나 confidence가 0.70 미만이면 생성하지 않는다.

## Severity 경계

- 최종 severity를 계산하지 않는다.
- 결합 승격이나 완화를 적용하지 않는다.
- `candidate_decisions.base_severity`는 후보 Rule의 Rule Base 값을 그대로 쓴다.
- `semantic_findings.severity`도 해당 Rule Base 값을 그대로 쓴다.
- 현재 Rule Base 값은 DA-03·DA-04·DA-15=`HIGH`, DA-12=`REVIEW`다.

## Finding 근거

- `semantic_findings`는 기존 Detection 구조를 사용한다.
- `observation`에는 화면에서 직접 관찰한 사실을, `why`에는 그 사실이 Rule을 충족하는 이유를 쓴다.
- `bbox`는 주 근거 요소의 화면 기준 정규화 좌표 `[x, y, width, height]`로 기록한다.
- `where.screen_ids`에는 근거가 실제로 존재하는 화면만 입력 순서대로 기록한다.
- DA-03은 대립 선택지 관계가 필요하므로 상대 요소를 `related_elements`에 최소 한 개 기록한다.
- 같은 Rule과 같은 요소의 결과를 중복 생성하지 않는다.

`audit_id`, `schema_version`, `screens`는 입력값을 그대로 복사하고 설명이나 Markdown 없이 JSON Schema에 맞는 JSON만 반환한다.
