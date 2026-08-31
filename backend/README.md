# DarkAudit Backend

## Setup

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run without model costs

Set `DARKAUDIT_PROVIDER=fake` in the root `.env`, then run:

```powershell
.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Copy `frontend/.env.example` to `frontend/.env.local` and set:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
VITE_USE_MOCKS=false
```

Start the frontend with `npm run dev` from `frontend/`.

## Run with OpenAI

```dotenv
DARKAUDIT_PROVIDER=openai
DARKAUDIT_MODEL=YOUR_VISION_CAPABLE_MODEL
OPENAI_API_KEY=YOUR_KEY
```

Uploaded images are stored under `data/uploads/` and excluded from Git.

## Test

```powershell
.venv\Scripts\python.exe -m unittest discover -s ai/tests -v
.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
```
