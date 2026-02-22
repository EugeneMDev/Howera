
# Golden Path (E2E) — v1 MVP

The Golden Path is the single most important test scenario.
It defines the **minimum end-to-end behavior** that must remain working.

This scenario should be runnable:
- with mocked providers (default)
- optionally with real Firebase/OpenAI (integration mode)

---

## 1. Objective

Prove that a user can:
1) Create project
2) Create job
3) Confirm upload (simulate video present)
4) Start workflow
5) Receive transcript + draft
6) Edit instruction
7) Extract screenshot (async) and poll task
8) Export MD bundle and PDF

Status semantics used in this scenario:
- `DRAFT_READY` means LLM draft generation is complete and draft artifact is stored.
- `DONE` means at least one export is completed successfully and retrievable.
- Export status FSM is `REQUESTED -> RUNNING -> SUCCEEDED|FAILED`.

---

## 2. Preconditions

### Services
- API running on `http://localhost:8000`
- n8n running and reachable
- `.env` configured (or mocks enabled)

### Auth
- Use a valid JWT (Firebase) OR a test bypass only if explicitly implemented.

---

## 3. Data Fixtures (Mock Mode)

Mock provider outputs must be deterministic:
- Transcript segments: fixed JSON (3–10 segments)
- Draft markdown: stable markdown with block markers (or add block markers on save)

Video fixture (optional for local extraction test):
- `fixtures/sample.mp4` (short, few seconds)

---

## 4. Scenario Steps

### Step 1 — Create Project
Request:
- `POST /projects` with `{ "name": "Demo Project" }`

Expected:
- `201`
- response has `project.id`

### Step 2 — Create Job
Request:
- `POST /projects/{projectId}/jobs`

Expected:
- `201`
- `job.status == CREATED`

### Step 3 — Confirm Upload
Goal: Move to `UPLOADED` without implementing full client upload.

Request:
- `POST /jobs/{jobId}/confirm-upload`
- Provide video manifest update (as per API contract), e.g. `video_uri`

Expected:
- `200` or `204` (as defined)
- `job.status == UPLOADED`

### Step 4 — Run Workflow
Request:
- `POST /jobs/{jobId}/run`

Expected:
- `202`
- `job.status` becomes `AUDIO_EXTRACTING`
- Orchestrator is triggered

### Step 5 — Workflow Callback(s)
n8n (or mock harness) calls internal endpoint:
- `POST /internal/jobs/{jobId}/status`
Headers/body must include:
- `event_id` (unique)
- `status`

Sequence:
1) `AUDIO_READY` + `audio_uri`
2) `TRANSCRIPT_READY` + `transcript_uri`
3) `DRAFT_READY` + `draft_uri`

Expected:
- each callback returns `204`
- duplicate event_id returns `200` with replay marker and no changes (idempotency)

### Step 6 — Load Draft Instruction
Request:
- `GET /instructions/{instructionId}` (or via job reference)

Expected:
- markdown exists
- contains stable anchors (Block IDs recommended)

### Step 7 — Save Edits
Request:
- `PUT /instructions/{instructionId}` with updated markdown

Expected:
- `200`
- `version` increments

### Step 8 — Extract Screenshot
Request:
- `POST /jobs/{jobId}/screenshots/extract`
Body:
- `timestamp_ms`
- `offset_ms` optional

Expected:
- `202`
- returns screenshot `task_id`

### Step 8b — Poll Screenshot Task
Request:
- `GET /screenshot-tasks/{taskId}`

Expected:
- `200`
- task status eventually `SUCCEEDED`
- resulting anchor/asset identifiers are available from task outcome or linked anchor lookup

### Step 9 — Export MD bundle
Request:
- `POST /jobs/{jobId}/exports` with `format=MD_ZIP`

Expected:
- `202`
- export status eventually `SUCCEEDED`
- `job.status` eventually becomes `DONE` after first successful export completion
- download_url available

### Step 10 — Export PDF
Request:
- `POST /jobs/{jobId}/exports` with `format=PDF`

Expected:
- `202` then export `SUCCEEDED`
- `job.status` remains `DONE`

---

## 5. Assertions (Must Hold)

- FSM rules enforced:
  - cannot run before upload confirmed
  - cannot transcribe before audio ready (unless resume rules)
- Idempotency:
  - same event_id does not double-transition
- Artifacts:
  - manifest URIs updated as pipeline progresses
- Export:
  - export artifacts stored and downloadable
  - export status transitions to `SUCCEEDED` before download URL is available
  - `DONE` job status is reached only after at least one export is `SUCCEEDED`

---

## 6. Test Harness Recommendation

Create a single test entrypoint:
- `tests/e2e/test_golden_path.py`

Modes:
- default mock mode (no external calls)
- integration mode (requires Firebase/OpenAI)

CI gate:
- mock mode must run on every PR
- integration mode optional / nightly
