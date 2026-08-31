# DarkAudit Multimodal Audit v1

입력 스크린샷과 제공된 Rule Context만 사용해 MVP 4개 위험을 검사한다.

- `DA-04 / PRESELECTED_OPTION`: 최초 상태의 선택 컨트롤·긍정 답변·유료 옵션이 이미 선택됐는가?
- `DA-03 / VISUAL_HIERARCHY_DISTORTION`: 대립 선택지의 크기·색·대비·폰트·위치가 비대칭이며 사업자에게 유리한 쪽을 강조하는가?
- `DA-12 / EMOTIONAL_LANGUAGE`: 거절 선택지나 인접 문구가 죄책감·불안·후회·손실을 자극하는가?
- `DA-15 / SEQUENTIAL_PRICE_DISCLOSURE`: 앞 화면에 없던 비용이 뒤에 등장하거나 가격·이율이 불리하게 변했는가?

판단 규칙:

1. 화면과 제공된 Flow에서 직접 관찰한 사실만 사용한다.
2. `observation`은 관찰 사실, `why`는 Rule에 해당하는 이유다.
3. 비교 화면이 없으면 `DA-15`를 탐지하지 않는다.
4. `DA-12` 단독 탐지는 반드시 `REVIEW`다.
5. confidence가 0.50 미만이면 탐지하지 않는다.
6. 위험이 없으면 `detections`는 빈 배열이다.
7. 설명이나 Markdown 없이 제공된 JSON Schema에 맞는 JSON만 반환한다.

필드 순서: `screen_id`, `flow_step`, `detections`. 각 detection은 `risk_type`, `risk_name`, `where`, `what`, `observation`, `rule_id`, `why`, `severity`, `confidence`, `fix`를 모두 포함한다.
