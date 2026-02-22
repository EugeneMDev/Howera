# Developer Setup (v1 MVP) - FastAPI + Firebase + n8n + OpenAI

This guide prepares a local development environment suitable for **agentic development** with Codex.

Applies to:
- v1 MVP (Firebase + OpenAI)
- Base setup for v2/v3 (additional steps noted)

---

## 1. Prerequisites

### OS tools

- `git`
- `make`
- `docker` + `docker compose`
- `ffmpeg` (local binary accessible to API container or host)

Verify:

```bash
ffmpeg -version
docker --version
docker compose version
```

### Python

Python 3.11+ is recommended.

Choose one dependency manager and stick to it:
- `uv` (recommended)
- `poetry`

Rule: do not mix multiple package managers.

---

## 2. Repository Layout Expectations

Required directories/files (minimum):

- `apps/api` (FastAPI backend)
- `spec/` (read-only contracts)
- `.env.example`
- `env.md`

---

## 3. Environment Variables

Copy env template:

```bash
cp .env.example .env
```

Fill required v1 variables (minimum).

Firebase:
- `FIREBASE_PROJECT_ID`
- `FIREBASE_CLIENT_EMAIL`
- `FIREBASE_PRIVATE_KEY`
- `FIREBASE_STORAGE_BUCKET`

OpenAI:
- `OPENAI_API_KEY`

n8n:
- `N8N_WEBHOOK_URL`
- `N8N_INTERNAL_CALLBACK_SECRET`

ffmpeg:
- `FFMPEG_PATH`

See details: `env.md`.

Do not commit `.env`.

---

## 4. Backend (FastAPI) - Local Run

From repo root.

### Option A - uv (recommended)

```bash
cd apps/api
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
make check
make run
```

### Option B - poetry

```bash
cd apps/api
poetry install
poetry run make check
poetry run make run
```

Health check:

```bash
curl -s http://localhost:8000/healthz
```

OpenAPI:

```bash
curl -s http://localhost:8000/openapi.json | head
```

---

## 5. n8n - Local Workflow Runner

Start n8n:

```bash
docker compose -f infra/n8n/docker-compose.yml up -d
```

Confirm:

- UI: `http://localhost:5678`
- Webhook URL matches your `.env` `N8N_WEBHOOK_URL`

Required webhooks (v1 minimum):

- `job-run` webhook (trigger pipeline)
- `job-status-callback` webhook (call API internal status endpoint)

Security:

- n8n must send `X-Event-Id` (or body `event_id`) and callback secret.

---

## 6. Firebase Setup (v1)

Recommended for dev:

- Use a dedicated Firebase project for development.
- Use Firebase Admin SDK credentials.
- Use Firebase Storage bucket for artifacts.

Notes:

- For local test runs, prefer FakeRepo to avoid cloud dependency.
- Integration tests may be gated behind `RUN_INTEGRATION_TESTS=true`.

---

## 7. Running the Golden Path (Developer)

The golden path is the main confidence gate.

See `docs/golden-path.md`.

Minimum expectation:

- API running
- n8n running
- `.env` configured (or mocks enabled)

---

## 8. Troubleshooting

### "401 Unauthorized"

- Missing/invalid JWT in `Authorization` header.
- Firebase project mismatch.
- Local dev may use `DEV_AUTH_BYPASS=true` only if explicitly added by spec (avoid if possible).

### "n8n webhook not reached"

- Ensure `N8N_WEBHOOK_URL` is reachable from API (container network vs host network).
- If API runs in Docker, use `http://n8n:5678/...` inside compose network.

### "ffmpeg not found"

- Set `FFMPEG_PATH`.
- If running in container, ffmpeg must exist in container image.

---

## 9. Phase Notes

### v2 Hybrid

- Set `LLM_PROVIDER=local`.
- Set `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL`.
- Enable `FEATURE_LOCAL_LLM_ENABLED=true`.

### v3 On-Prem

Switch auth/storage/db:

- `KEYCLOAK_ENABLED=true`
- `DATABASE_ENABLED=true`
- `STORAGE_PROVIDER=minio`

Use compose/k8s infra under `infra/compose` or `infra/k8s`.
