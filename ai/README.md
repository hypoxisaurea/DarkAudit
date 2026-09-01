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

## Audit a website URL

Install the Playwright browser once after installing Python dependencies:

```powershell
.venv\Scripts\python.exe -m playwright install chromium
```

Capture desktop and mobile screenshots without an AI navigation cost:

```powershell
.venv\Scripts\python.exe -m ai.cli capture-url `
  --url https://example.com `
  --mode quick
```

Run safe Computer Use exploration before the existing screenshot audit:

```powershell
.venv\Scripts\python.exe -m ai.cli audit-url `
  --url https://example.com `
  --mode smart `
  --model $env:DARKAUDIT_MODEL `
  --computer-model $env:DARKAUDIT_COMPUTER_MODEL
```

`quick` captures the initial viewport and full page for each requested device profile.
`smart` adds a screenshot-first Computer Use loop. The local policy only permits reversible
navigation and blocks typing, form submission, purchase/registration actions, private-network
targets, cross-origin navigation, downloads, and popups. Use `--allow-private-network` only for
explicit local development targets.

Screenshots are written beneath `data/captures/<audit-id>/<profile>/` by default. URL capture
manifests also contain visible text and interactive-element geometry for future deterministic
rules. The final multimodal audit still receives at most five evenly sampled screenshots to
preserve the current `LLMAuditRequest` contract.
