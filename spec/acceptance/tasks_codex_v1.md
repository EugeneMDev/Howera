# Codex Task Pack — v1 (FastAPI)

This document defines the exact sequence of tasks Codex must execute.
Each task must:

- Modify only allowed files
- Pass make check
- Produce minimal diff
- Provide short change summary

---

# GLOBAL RULES

1. spec/ is read-only.
2. One task = one logical change.
3. No refactors unless explicitly requested.
4. All external integrations must use adapters.
5. No business logic inside route functions.

---

# TASK 00 — Project Scaffold

Goal:
- Create FastAPI project structure
- Add Makefile with:
  make lint
  make test
  make check
  make run

Allowed paths:
- apps/api/**

Acceptance:
- make check passes
- /healthz endpoint works

---

# TASK 01 — OpenAPI Skeleton Routes

Goal:
- Implement route skeletons based on spec/api/openapi.yaml
- Return 501 for now

Allowed:
- apps/api/app/routes/**
- apps/api/app/schemas/**

Acceptance:
- /openapi.json generated
- Smoke test verifies key paths exist

---

# TASK 02 — FSM Domain Layer

Goal:
- Implement JobStatus enum
- Implement allowed transitions
- Implement ensure_transition()

Allowed:
- apps/api/app/domain/job_fsm.py
- tests/domain/test_job_fsm.py

Acceptance:
- All transition tests pass

---

# TASK 03 — Repository Abstraction

Goal:
- Define abstract repos:
  ProjectRepo
  JobRepo
  InstructionRepo
- Implement FirestoreRepo
- Implement FakeRepo for tests

Acceptance:
- Tests use FakeRepo
- No direct Firestore calls in routes

---

# TASK 04 — Firebase Auth Middleware

Goal:
- Implement JWT verification dependency
- Inject authenticated `user_id` (application role is `editor`)

Acceptance:
- Unauthorized request returns 401
- Authorized request passes

---

# TASK 05 — Projects API Implementation

Goal:
- Implement CRUD logic
- Use repo layer

Acceptance:
- Tests pass for create → list → get

---

# TASK 06 — Jobs API Implementation

Goal:
- Implement create job
- Return manifest
- Enforce FSM

Acceptance:
- Job created with status CREATED

---

# TASK 07 — Upload Confirmation

Goal:
- confirm-upload endpoint
- FSM transition to UPLOADED

Acceptance:
- Illegal transition rejected

---

# TASK 08 — Run + Workflow Callback

Goal:
- Implement /run
- Implement internal status callback
- Idempotency support
- Callback auth via `X-Callback-Secret`

Acceptance:
- Callback twice does not duplicate state change
- Callback payload includes `event_id`, `status`, `occurred_at`

---

# TASK 09 — Instruction CRUD

Goal:
- Implement get/save instruction
- Version increment

Acceptance:
- Version increments on save

---

# TASK 10 — Regenerate Task Model

Goal:
- Implement async-style regenerate endpoint
- Task state tracking
- Implement task poll endpoint (`GET /tasks/{taskId}`)

Acceptance:
- Poll returns SUCCEEDED

---

# TASK 11 — Screenshot Extraction

Goal:
- Implement server-side frame extraction
- Persist asset reference

Acceptance:
- Test extraction on small sample

---

# TASK 12 — Export Pipeline

Goal:
- Implement MD bundle export
- Implement PDF export

Acceptance:
- Export artifact stored
- Download link works
