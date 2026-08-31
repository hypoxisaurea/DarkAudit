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

단일 패턴 쌍이 있어야 "체크박스 기본값만 뒤집었을 때 해당 유형 탐지가 사라지는가"를
다른 패턴의 간섭 없이 측정할 수 있다.
