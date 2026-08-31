# DarkAudit AI Baseline

## Setup

```powershell
python -m pip install -r requirements.txt
```

## Run

```powershell
python -m ai.cli audit `
  --image .\screen_01.png --flow-step 상품안내 `
  --image .\screen_02.png --flow-step 결제
```

The CLI accepts one to five images in Flow order and writes JSON only. The selected model must support image input and Structured Outputs in the Responses API.

## Test

```powershell
python -m unittest discover -s ai/tests -v
```

Unit tests use a fake provider and do not require an API key.

Copy `.env.example` to `.env`, then fill in the local values. Never commit `.env`.
