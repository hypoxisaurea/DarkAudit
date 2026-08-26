# DarkAudit

생성형 AI 기반 금융 UX Compliance Assistant

금융위원회 「온라인 금융상품 판매 관련 다크패턴 가이드라인」(2025.12) 의 4개 범주·15개 세부 유형을
기준으로 금융상품 가입 Flow 화면을 사전 점검하는 B2B2C 웹서비스.

2026 금융 AI Challenge 출품작.

## 구조

```
rules/          금융위 15개 유형 Machine-readable Rule Base   [Team B]
data/           Synthetic Financial UI Dataset                [Team B]
backend/        FastAPI · Rule Engine · DB                    [Team B]
frontend/       React                                         [Team B]
ai/             OCR / UI Parsing / Multimodal LLM Pipeline    [Team A]
docs/           스키마 · 아키텍처 · 기획 문서                  [공동]
```

## Rule Base

`rules/dark_pattern_rules.yaml` 이 원본이며 JSON 은 빌드 산출물이다.
규칙 수정은 YAML 에서만 하고, 반드시 검증을 거쳐 JSON 을 재생성한다.

```bash
cd rules
pip install pyyaml
python build_rules.py --summary
```

검증 항목: 필수 필드, rule_id 중복, 범주별 개수 정합성,
combination_amplifiers 참조 무결성, standalone_sufficient 승격 경로 존재 여부.

### 설계 원칙

| 구분 | 담당 |
| --- | --- |
| `deterministic_checks` | 코드가 계산 — 선택 상태, 크기비, 대비비, 클릭 수, 가격 변화 |
| `semantic_checks` | Multimodal LLM 이 해석 — 의미, 맥락, 시각적 위계의 함의 |

`standalone_sufficient: false` 인 유형(DA-09 · DA-12 · DA-13 · DA-14)은 단독으로 HIGH 를
부여하지 않는다. 가이드라인이 해당 행위 자체는 문제되지 않으며 다른 행위와 결합할 때
문제가 된다고 명시하고 있기 때문이다.

## 브랜치

```
main
└── develop
    ├── feature/ai-pipeline
    ├── feature/rule-dataset
    ├── feature/backend-api
    ├── feature/frontend
    └── feature/deploy
```

feature → develop → main 순서로 병합한다.

## 팀

| 담당 | 역할 |
| --- | --- |
| 배소연 | AI Engineer — Multimodal LLM 기반 UX Risk Detection Pipeline |
| 이정현 | Data Engineer — 규제 데이터 Pipeline 및 Backend / Deployment |
