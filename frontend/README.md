# DarkAudit Frontend

## Local development

```powershell
npm install
Copy-Item .env.example .env.local
npm run dev
```

`VITE_USE_MOCKS=true` keeps all API calls in the browser through MSW. To use FastAPI, set
`VITE_USE_MOCKS=false` and configure `VITE_API_BASE_URL`.

## Backend contract

The frontend currently calls:

- `GET /api/v1/dashboard/summary`
- `POST /api/v1/audits`
- `POST /api/v1/audits/{auditId}/screens` (`multipart/form-data`)
- `POST /api/v1/audits/{auditId}/analyze`
- `GET /api/v1/analysis-jobs/{jobId}`
- `PATCH /api/v1/findings/{findingId}`

Requests include cookies and, when available, the `darkaudit.accessToken` session-storage value as
a Bearer token. Upload requests use a two-minute timeout; other requests use 30 seconds.

After FastAPI is running on port 8000, regenerate its TypeScript contract with:

```powershell
npm run api:types
```

## Quality checks

```powershell
npm run build
npm run lint
npm run test
npm run test:e2e
```

Visual snapshots cover 1440px desktop and 390px mobile viewports. Run `npm run
test:e2e:update` only after intentionally reviewing a UI change. Lighthouse expects a production
preview on port 4173 and writes its report to `reports/lighthouse.json`.
