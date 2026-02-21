# Environment Configuration Guide

This document describes all environment variables required for Howera
across deployment phases:

- v1 — Firebase + OpenAI
- v2 — Hybrid (Firebase + Local LLM)
- v3 — On-Prem (Keycloak + PostgreSQL + MinIO + Local LLM)

The `.env.example` file is the source template.
Production secrets must NEVER be committed.

---

# 1. Core Application Settings

| Variable | Required | Phase | Description |
|----------|----------|-------|------------|
| APP_ENV | Yes | All | development / staging / production |
| APP_NAME | Yes | All | Application name |
| LOG_LEVEL | Yes | All | Logging verbosity |
| HOST | Yes | All | Server bind address |
| PORT | Yes | All | API port |

---

# 2. Authentication

## v1 / v2 — Firebase

Required:
- FIREBASE_PROJECT_ID
- FIREBASE_CLIENT_EMAIL
- FIREBASE_PRIVATE_KEY
- FIREBASE_STORAGE_BUCKET

Notes:
- Use Firebase Admin SDK.
- PRIVATE_KEY must be stored securely (secret manager in production).
- Do NOT log full private key.

## v3 — Keycloak

Enable:
KEYCLOAK_ENABLED=true

Required:
- KEYCLOAK_SERVER_URL
- KEYCLOAK_REALM
- KEYCLOAK_CLIENT_ID
- KEYCLOAK_CLIENT_SECRET

Security:
- Always validate JWT audience and issuer.
- Use HTTPS in production.

---

# 3. Database

v1 / v2:
- Firestore (implicit via Firebase)

v3:
DATABASE_ENABLED=true
DATABASE_URL=postgresql+psycopg://...

Requirements:
- SSL required in production.
- Migrations must be versioned.

---

# 4. Storage

STORAGE_PROVIDER determines active backend.

## v1 / v2
STORAGE_PROVIDER=firebase

## v3
STORAGE_PROVIDER=minio
MINIO_ENDPOINT=
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_BUCKET=

Security:
- Use signed URLs for all downloads.
- Enforce TTL via SIGNED_URL_TTL_SECONDS.
- Never expose internal storage paths directly.

---

# 5. Workflow (n8n)

WORKFLOW_ENABLED=true

Required:
- N8N_WEBHOOK_URL
- N8N_INTERNAL_CALLBACK_SECRET

Security:
- Internal callback must validate secret.
- Reject callbacks without valid X-Event-Id.

---

# 6. LLM Configuration

LLM_PROVIDER=openai | local

## v1 (OpenAI)
Required:
- OPENAI_API_KEY
- LLM_MODEL

## v2 / v3 (Local)
Required:
- LOCAL_LLM_BASE_URL
- LOCAL_LLM_MODEL

Rules:
- Adapter layer must be used.
- Do not call provider directly in route handlers.
- Timeout must be enforced.

---

# 7. STT Configuration

STT_PROVIDER=openai | local

## v1
OPENAI_STT_MODEL

## v2 / v3
LOCAL_STT_BASE_URL
LOCAL_STT_MODEL

Rules:
- Must return structured transcript segments.
- Errors must map to RETRYABLE / NON_RETRYABLE taxonomy.

---

# 8. Screenshot Extraction

Required:
- FFMPEG_PATH

Optional:
- SCREENSHOT_STRATEGY
- SCREENSHOT_MAX_RESOLUTION

Rules:
- Extraction must be server-side.
- No video decoding in frontend.
- Validate timestamp bounds before extraction.

---

# 9. Export Settings

EXPORT_PROVIDER=playwright | weasyprint

Requirements:
- Export timeout enforced.
- Export must use flattened annotated images.
- Temp directory must be writable.

---

# 10. Idempotency & Security

| Variable | Description |
|----------|------------|
| IDEMPOTENCY_HEADER | Header name for workflow events |
| INTERNAL_API_SECRET | Secret for internal callbacks |
| SIGNED_URL_TTL_SECONDS | Expiration for generated URLs |

Rules:
- Workflow callbacks MUST include event_id.
- Duplicate event_id must not change state twice.
- Never expose INTERNAL_API_SECRET in logs.

---

# 11. Observability

ENABLE_METRICS=true
ENABLE_TRACING=false (optional)

Metrics should include:
- Job duration by stage
- LLM latency
- STT latency
- Export duration
- Failure rate

---

# 12. Feature Flags

Feature flags control phased rollout.

| Flag | Phase | Purpose |
|------|-------|--------|
| FEATURE_LOCAL_LLM_ENABLED | v2+ | Allow local provider |
| FEATURE_BLOCK_ID_ENFORCED | v2+ | Require stable markdown anchors |
| FEATURE_ON_PREM_MODE | v3 | Activate Postgres + MinIO + Keycloak |
| FEATURE_REGENERATE_ENABLED | v1+ | Enable fragment regenerate |
| FEATURE_SCREENSHOT_ANNOTATION_ENABLED | v1+ | Enable annotation subsystem |

Rules:
- Feature flags must not bypass FSM rules.
- Feature flags must be checked centrally (not scattered).

---

# 13. Required Variables by Phase

## v1 MVP
Required:
- Firebase variables
- OPENAI_API_KEY
- N8N_WEBHOOK_URL
- FFMPEG_PATH

## v2 Hybrid
Required:
- Firebase variables
- LOCAL_LLM_BASE_URL
- LOCAL_STT_BASE_URL
- Feature flags enabled

## v3 On-Prem
Required:
- KEYCLOAK_*
- DATABASE_URL
- MINIO_*
- LOCAL_LLM_BASE_URL
- LOCAL_STT_BASE_URL
- FEATURE_ON_PREM_MODE=true

---

# 14. Production Security Requirements

- All secrets must be stored in:
  - Vault
  - Kubernetes secrets
  - Cloud secret manager
- `.env` must never be committed.
- Logs must redact:
  - API keys
  - JWTs
  - Storage credentials

---

# 15. Validation Requirements (Spec-Driven)

On application startup:
- Validate required variables for selected phase.
- Fail fast if required variables missing.
- Log active configuration (excluding secrets).
- Enforce consistency:
  - If STORAGE_PROVIDER=minio → DATABASE_ENABLED must be true.
  - If LLM_PROVIDER=local → LOCAL_LLM_BASE_URL required.
  - If KEYCLOAK_ENABLED=true → FIREBASE auth disabled.

---

# 16. Agent Development Rule

Codex must:
- Never hardcode environment variables.
- Always read from centralized Settings class.
- Never introduce new env variables without updating:
  - `.env.example`
  - `docs/env.md`