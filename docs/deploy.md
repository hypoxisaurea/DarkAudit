# 배포 가이드 (Render + Vercel)

로컬에서 `docker build` + 컨테이너 실행 + Playwright/Chromium 동작까지 확인한
구성이다. Render 무료 티어는 카드 등록 없이 GitHub 저장소만 연결하면 되고,
Vercel도 동일하게 zero-config로 Vite 빌드를 인식한다.

## 순서 (역방향 의존성이 있어 이 순서를 지켜야 한다)

1. **백엔드(Render)를 먼저 배포**해서 URL을 받는다.
2. 그 URL을 **프론트(Vercel) 환경변수**에 넣고 배포해서 프론트 URL을 받는다.
3. 프론트 URL을 다시 **백엔드 CORS 환경변수**에 넣고 재배포한다.

## 1. 백엔드 — Render

레포가 **public**이라 GitHub 계정 연동 없이 바로 된다 (git 히스토리에 시크릿
없는 것 확인 완료 — `.env`는 커밋된 적 없음).

1. https://render.com 가입 (카드 등록 불필요).
2. **New +** → **Web Service** → **Public Git Repository** 선택 → 이 저장소의
   HTTPS URL(`https://github.com/hypoxisaurea/DarkAudit`) 입력.
   - Runtime은 **Docker**, Dockerfile 경로는 `./Dockerfile` (레포 루트에 있음).
   - GitHub 계정을 연동해서 Blueprint(`render.yaml` 자동 인식)로 하고 싶다면
     그 방법도 되지만, public repo면 이 방법이 로그인 단계가 없어 더 빠르다.
3. 아래 환경변수를 Render 대시보드에서 채운다:
   - `DARKAUDIT_MODEL` — 실제 사용할 모델명
   - `OPENAI_API_KEY`
   - `FIGMA_ACCESS_TOKEN` — Figma 임포트 데모 안 하면 생략 가능
   - `DARKAUDIT_CORS_ORIGINS` — 지금은 임시로 `http://localhost:5173` 등 아무 값이나 넣어두고, 3단계에서 실제 프론트 URL로 교체한다.
4. 배포가 끝나면 `https://<서비스명>.onrender.com` 형태의 URL이 생긴다. **이 URL을 적어둔다.**
   - Public Repository 방식은 push해도 자동 재배포가 안 될 수 있다 — 코드를
     더 올린 뒤 반영하려면 Render 대시보드에서 **Manual Deploy → Deploy latest commit**을 눌러야 한다.
5. `curl https://<서비스명>.onrender.com/health` → `{"status":"ok"}` 확인.

무료 티어는 15분 미사용 시 슬립된다. **데모 시작 5~10분 전에 위 health 체크로 한 번 깨워두는 걸 잊지 말 것** — 슬립 상태에서 첫 요청은 콜드스타트로 30초 이상 걸릴 수 있다.

## 2. 프론트 — Vercel

1. https://vercel.com 가입 → GitHub 연결 → 이 저장소 Import.
2. **Root Directory**를 `frontend`로 지정 (Vercel이 자동으로 Vite를 인식해서 build/output 설정은 안 건드려도 된다).
3. 환경변수 추가:
   - `VITE_API_BASE_URL` = 1단계에서 받은 Render URL (예: `https://darkaudit-backend.onrender.com`, 끝에 슬래시 없이)
   - `VITE_USE_MOCKS` = `false` (안 넣으면 목업 모드로 떠서 실제 백엔드를 안 탄다 — 데모 중 이걸로 헤매기 쉬우니 꼭 확인)
4. Deploy. 끝나면 `https://<프로젝트명>.vercel.app` URL이 생긴다.

## 3. 백엔드 CORS 마무리

1. Render 대시보드로 돌아가서 `DARKAUDIT_CORS_ORIGINS`를 2단계에서 받은 Vercel URL로 교체한다(예: `https://darkaudit.vercel.app`, 콤마로 여러 개 가능).
2. 저장하면 Render가 자동 재배포한다.
3. 실제 배포된 프론트 URL에 접속해서 진단 생성 → 업로드/분석까지 한 번 끝까지 눌러본다. 브라우저 개발자도구 콘솔에 CORS 에러가 뜨면 이 값이 정확한지(오타, `https` 누락, 끝 슬래시 등) 다시 확인.

## 로컬에서 이미지만 먼저 확인하고 싶을 때

```bash
docker build -t darkaudit-backend .
docker run -p 8000:8000 -e DARKAUDIT_PROVIDER=fake darkaudit-backend
curl http://localhost:8000/health
```

`DARKAUDIT_PROVIDER=fake`면 OpenAI 호출 없이 배선만 확인한다(탐지 결과는 항상
0건). 실제 모델 응답까지 보려면 `DARKAUDIT_PROVIDER=openai`로 바꾸고
`DARKAUDIT_MODEL`/`OPENAI_API_KEY`를 같이 넘긴다.

## 알아둘 것

- SQLite 파일(`data/darkaudit.db`)은 컨테이너 안에 있어 **재배포·재시작하면 초기화된다.** 데모 중간에 Render가 재시작하면 그동안 만든 진단 데이터가 날아간다 — 데모 시작 직전에 필요한 진단을 새로 만드는 걸 권장.
- 이미지가 2GB 정도로 크다(Chromium 포함). Render 무료 빌드 시간 안에는 들어오지만, 빌드가 몇 분 걸릴 수 있다.
- 로그 확인: Render 대시보드 → 서비스 → **Logs** 탭에서 실시간으로 본다. `_fail_job()`이 기록한 에러 메시지는 API 응답(`GET /api/v1/analysis-jobs/{id}`의 `error` 필드)에도 그대로 나온다.
