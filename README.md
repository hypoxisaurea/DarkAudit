# DarkAudit

생성형 AI로 금융상품 가입 화면의 다크패턴을 점검하는 UX 컴플라이언스 도구입니다.
금융위원회 「온라인 금융상품 판매 관련 다크패턴 가이드라인」(2025.12)의 4개 범주,
15개 세부 유형을 기계 판독 가능한 규칙으로 관리하고, 여러 화면으로 이루어진 가입 흐름을
분석해 위험 요소와 개선 권고안을 제공합니다.

2026 금융 AI Challenge 출품작입니다.

## 현재 구현 범위

- React 기반 Audit 생성 및 결과 검토 화면
- FastAPI 기반 Audit 생성, 화면 업로드, 분석 작업 조회, Finding 상태 변경 API
- OpenAI Responses API를 이용한 멀티모달 분석과 비용 없는 Fake provider
- MVP 규칙 `DA-03`, `DA-04`, `DA-12`, `DA-15` 탐지
- 15개 다크패턴 유형의 YAML Rule Base와 검증/JSON 빌드 도구
- Risky/Clean 쌍으로 구성된 Synthetic UI 데이터셋 생성 및 라벨 검수 도구

현재 백엔드와 AI 분석기는 Audit 하나당 순서가 있는 이미지 **1~5개**를 처리합니다.
데이터는 메모리에 저장되므로 백엔드를 재시작하면 Audit과 분석 결과가 초기화됩니다.
업로드한 이미지는 `data/uploads/`에 저장됩니다.

## 프로젝트 구조

```text
ai/          멀티모달 분석 파이프라인, provider, 스키마, 평가 코드
backend/     FastAPI API와 Audit 실행 오케스트레이션
frontend/    React, TypeScript, Vite 기반 웹 애플리케이션
rules/       15개 유형 Rule Base와 검증/빌드 스크립트
data/        Synthetic UI 생성 설정, 라벨, 검수 도구
docs/        라벨링 가이드와 프로젝트 문서
```

세부 내용은 [AI](ai/README.md), [Backend](backend/README.md),
[Frontend](frontend/README.md), [Dataset Generator](data/generator/README.md) 문서를 참고하세요.

## 빠른 시작

필요 환경은 Python 3.10 이상과 Node.js 20 이상입니다.

### 1. Python 환경 구성

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. 백엔드 실행

모델 호출 없이 전체 흐름을 확인하려면 저장소 루트에 `.env`를 만들고 Fake provider를
사용합니다. Fake provider는 분석을 성공 처리하지만 Finding은 생성하지 않습니다.

```dotenv
DARKAUDIT_PROVIDER=fake
```

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

`http://localhost:8000/health`에서 상태를, `http://localhost:8000/docs`에서 API 문서를
확인할 수 있습니다.

실제 AI 분석에는 다음 환경 변수가 필요합니다.

```dotenv
DARKAUDIT_PROVIDER=openai
DARKAUDIT_MODEL=YOUR_VISION_CAPABLE_MODEL
OPENAI_API_KEY=YOUR_KEY
```

선택한 모델은 Responses API의 이미지 입력과 Structured Outputs를 지원해야 합니다.
`.env.example`을 시작점으로 사용할 수 있으며 `.env`는 Git에 커밋하지 않습니다.

### 3. 프런트엔드 실행

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

브라우저에서 `http://localhost:5173`을 엽니다. 실제 백엔드와 연결하려면
`frontend/.env.local`을 다음과 같이 설정합니다.

```dotenv
VITE_API_BASE_URL=http://localhost:8000
VITE_USE_MOCKS=false
```

`VITE_USE_MOCKS=true`이면 백엔드 없이 브라우저 내 MSW mock API로 화면을 확인할 수
있습니다.

## CLI 분석

웹 애플리케이션을 거치지 않고 이미지 1~5개를 순서대로 분석할 수도 있습니다.
CLI는 OpenAI provider를 사용하며 결과 JSON만 표준 출력으로 내보냅니다.

```bash
python -m ai.cli audit \
  --image ./screen_01.png --flow-step "상품 안내" \
  --image ./screen_02.png --flow-step "결제"
```

`DARKAUDIT_MODEL`과 `OPENAI_API_KEY`를 설정하거나 모델을 `--model`로 전달해야 합니다.

## Rule Base

`rules/dark_pattern_rules.yaml`이 원본이며 `rules/dark_pattern_rules.json`은 Git에 포함하지
않는 빌드 산출물입니다. 규칙은 YAML에서만 수정한 뒤 검증과 빌드를 실행합니다.

```bash
python rules/build_rules.py --summary
```

빌드 과정은 필수 필드, `rule_id` 중복, 범주별 개수, 결합 규칙 참조 무결성,
단독 판정 불가 규칙의 승격 경로를 검증합니다.

| 구분 | 역할 |
| --- | --- |
| `deterministic_checks` | 선택 상태, 크기비, 대비비, 클릭 수, 가격 변화 등 코드로 계산 가능한 신호 |
| `semantic_checks` | 의미, 맥락, 시각적 위계의 함의 등 멀티모달 모델이 해석하는 신호 |

`standalone_sufficient: false`인 `DA-09`, `DA-12`, `DA-13`, `DA-14`는 단독으로 HIGH를
부여하지 않고 다른 행위와의 결합 여부를 함께 판단합니다.

## 검증

저장소 루트에서 Python 테스트를 실행합니다.

```bash
python -m unittest discover -s ai/tests -v
python -m unittest discover -s backend/tests -v
```

프런트엔드 검증은 `frontend/`에서 실행합니다.

```bash
npm run lint
npm run test
npm run build
```

Playwright 브라우저를 설치한 환경에서는 E2E와 접근성 테스트도 실행할 수 있습니다.

```bash
npx playwright install chromium
npm run test:e2e
npm run test:a11y
```

## 팀

| 담당 | 역할 |
| --- | --- |
| 배소연 | AI Engineer - Multimodal LLM 기반 UX Risk Detection Pipeline |
| 이정현 | Data Engineer - 규제 데이터 Pipeline 및 Backend / Deployment |
