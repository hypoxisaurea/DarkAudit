# Synthetic UI Generator

보험 가입 Flow 화면을 생성하고 스크린샷과 정답 라벨을 함께 만든다.

## 설계

화면 템플릿은 하나이며, 어떤 다크패턴을 심을지는 config 로 주입한다.
따라서 Risky / Clean 쌍은 **설정 한 줄만 다른 상태**가 구조적으로 보장된다.
손으로 두 화면을 만들면 무심코 다른 요소까지 바뀌는데 이 방식은 그럴 수 없다.

패턴이 걸린 요소에는 `data-da="DA-XX"` 속성이 남는다.
캡처 시 `getBoundingClientRect()` 로 bbox 를 자동 추출하므로 사람이 좌표를 찍지 않는다.

```
config → generate.py → HTML → capture.py → PNG + label.json
```

## 실행

```bash
pip install playwright jsonschema
playwright install chromium

python generate.py --config configs/ins-001-risky.json
python capture.py  --config configs/ins-001-risky.json
```

## config

| 키 | 설명 |
| --- | --- |
| `flow_id` | Flow 식별자 |
| `pair_id` | Risky/Clean 짝의 공통 ID |
| `variant` | `risky` / `clean` |
| `patterns` | 심을 rule_id 배열. 빈 배열이면 clean |
| `patterns` 의 `mitigate_DA-XX` | 해당 유형의 완화 요건을 충족시킨다. 유형은 유지되고 severity 만 1단계 하향 |
| `base_price` / `final_price` | DA-15 의 최초가·최종가 |

## 한계

자동 생성 라벨은 **의도적으로 심은 패턴만** 포함한다.
스타일링 과정에서 의도치 않게 발생한 패턴은 포함되지 않으므로
Gold Set 검수로 보완해야 한다. `docs/labeling_guide.md` 참고.

## 검수 도구

```bash
python inspect_labels.py            # 전체 검수 시트 + 인스턴스 분포
python inspect_labels.py --flow dep-001-risky
```

스크린샷 위에 라벨을 그린다. 빨간 실선이 primary, 파란 점선이 related.
`../synthetic/review/` 에 저장된다.

유형별 인스턴스가 3건 미만이면 경고한다. Recall 이 사실상 0/1 밖에 나오지 않아
지표로서 의미가 없기 때문이다.

## Flow 구성

| 종류 | 구성 | 용도 |
| --- | --- | --- |
| `ins-001`, `dep-001` | 복합 — P0 유형 전부 | 통합 시나리오, 결합 판정 |
| `ins-002`~`ins-008`, `dep-002` | 단일 패턴 — 유형 하나만 | Counterfactual Consistency 격리 측정 |
| `ins-009` | DA-04 + 완화 요건 | severity 하향 처리 검증 |

단일 패턴 쌍이 있어야 "체크박스 기본값만 뒤집었을 때 해당 유형 탐지가 사라지는가"를
다른 패턴의 간섭 없이 측정할 수 있다.

## element_id

`primary` 와 `related_elements` 에 DOM 기반 `element_id` 를 기록한다.

순번(`el_001`...)이 아니라 **태그 경로 + 클래스 + 텍스트 해시**로 만든다. 순번을 쓰면
요소가 하나만 추가돼도 뒤가 전부 밀려, Before/After 에서 고치지도 않은 문제가
"해결 + 신규 발생"으로 잡힌다.

실제로 복합 Flow 와 단일 패턴 Flow 는 화면 구성이 다르지만 같은 요소는 같은 id 를 받는다.

**평가의 주 키로 사용하지 않는다.** `element_id` 는 우리가 생성한 화면에만 존재하며
실제 서비스 입력인 스크린샷에는 없다. Localization 평가는 bbox(IoU) 로 하고,
`element_id` 는 Counterfactual 검증과 Before/After 매칭의 보조 키로만 쓴다.

## severity

자동 라벨의 severity 는 Rule Base 의 기본값을 따르며, 완화 요건을 충족하면 1단계 낮춘다.
최종 severity(결합 판정 포함)는 Backend 의 Rule Engine 이 계산한다.
