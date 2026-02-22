# Codex Task Pack — v1.1 (FastAPI)

This document defines the implementation sequence for the v1.1 contract.
Each task must:

- Modify only allowed files
- Pass make check
- Produce minimal diff
- Provide short change summary

---

# GLOBAL RULES

1. `spec/` is source of truth.
2. One task = one logical change.
3. No refactors unless explicitly requested.
4. All external integrations must use adapters.
5. No business logic inside route functions.
6. Unauthorized and nonexistent resources must use no-existence-leak policy where defined by contract.

---

# TASK 00 — Project Scaffold + Operational Health

Goal:
- Create FastAPI project structure and quality gates
- Add Makefile with:
  - `make lint`
  - `make test`
  - `make check`
  - `make run`
- Add operational `/healthz` endpoint (outside OpenAPI contract)

Allowed paths:
- `apps/api/**`

Acceptance:
- `make check` passes
- `/healthz` endpoint works
- `/healthz` is treated as operational endpoint and excluded from OpenAPI contract assertions

---

# TASK 01 — Contract Route Skeleton (No 501 Drift)

Goal:
- Implement route skeletons for all paths in `spec/api/openapi.yaml`
- Use request/response Pydantic schemas aligned to contract
- Avoid placeholder `501` responses that violate declared status behavior

Allowed:
- `apps/api/app/routes/**`
- `apps/api/app/schemas/**`

Acceptance:
- `/openapi.json` generated
- Smoke test verifies required paths exist
- Status codes and response bodies follow contract shapes

---

# TASK 02 — FSM Domain Layer (Terminal DONE)

Goal:
- Implement `JobStatus` enum and allowed transitions
- Implement `ensure_transition(old_status, new_status)`
- Enforce terminal immutability for `FAILED`, `CANCELLED`, `DONE`

Allowed:
- `apps/api/app/domain/job_fsm.py`
- `tests/domain/test_job_fsm.py`

Acceptance:
- Valid/invalid transition tests pass
- No transition out of terminal states

---

# TASK 03 — Repo Abstractions + Ownership Boundaries

Goal:
- Define abstract repos (`ProjectRepo`, `JobRepo`, `InstructionRepo`, `AnchorRepo`, `ExportRepo` as needed)
- Implement FakeRepo for deterministic tests
- Enforce per-user ownership filtering for editor-facing resources

Acceptance:
- Tests use FakeRepo where possible
- No direct storage/database calls in routes
- Ownership checks prevent cross-project data access

---

# TASK 04 — Authentication + Callback Secret + No-Leak 404

Goal:
- Implement bearer auth dependency for write endpoints
- Implement callback secret validation for `/internal/jobs/{jobId}/status`
- Apply no-existence-leak behavior where required by contract

Acceptance:
- Unauthorized write returns `401` where contract defines auth failure
- Unauthorized/nonexistent resource checks return same `404 RESOURCE_NOT_FOUND` shape where contract defines no-leak
- Callback secret enforced

---

# TASK 05 — Jobs Intake: Create/Get + Confirm Upload Idempotency

Goal:
- Implement `POST /projects/{projectId}/jobs`, `GET /jobs/{jobId}`
- Implement `POST /jobs/{jobId}/confirm-upload`
- Enforce same-URI replay, conflicting-URI `409`, and FSM validation

Acceptance:
- Job created with `CREATED`
- Confirm-upload transitions to `UPLOADED`
- Replay with same `video_uri` is no-op success
- Conflicting `video_uri` returns contract-defined `409`

---

# TASK 06 — Run/Cancel/Retry + Dispatch Safety

Goal:
- Implement `POST /jobs/{jobId}/run`
- Implement `POST /jobs/{jobId}/cancel`
- Implement `POST /jobs/{jobId}/retry`
- Ensure dispatch idempotency and upstream failure handling

Acceptance:
- Run: first `202`, replay `200`, no duplicate dispatch
- Cancel: FSM-governed
- Retry: allowed only from `FAILED`, checkpoint-aware metadata persisted
- Dispatch failures return contract-defined upstream error without illegal state advance

---

# TASK 07 — Internal Callback Idempotency + Ordering + Atomicity

Goal:
- Implement `/internal/jobs/{jobId}/status`
- Enforce callback semantics:
  - first accepted callback -> `204`
  - identical replay -> `200` with replay payload
  - replay payload mismatch -> `409 EVENT_ID_PAYLOAD_MISMATCH`
  - out-of-order non-monotonic event -> `409 CALLBACK_OUT_OF_ORDER`
- Apply FSM validation and transactional state+artifact updates

Acceptance:
- Duplicate callbacks do not duplicate side effects
- State/artifact/failure metadata remain consistent under failures
- Transition audit events emitted without duplicate business events on replay

---

# TASK 08 — Transcript Endpoint with State Gating

Goal:
- Implement `GET /jobs/{jobId}/transcript`
- Support pagination fields from contract
- Enforce allowed-state gating and no-leak policy

Acceptance:
- Returns contract-compliant paginated transcript
- Invalid state returns contract-defined conflict payload

---

# TASK 09 — Instruction Read/Write + Version Concurrency

Goal:
- Implement `GET /instructions/{instructionId}`
- Implement `PUT /instructions/{instructionId}` with `base_version` optimistic concurrency
- Persist validation fields (`validation_status`, etc.) as defined by contract

Acceptance:
- Latest/versioned retrieval works
- Stale `base_version` returns `409 VERSION_CONFLICT`

---

# TASK 10 — Regenerate Task Model (Idempotent + Provenance)

Goal:
- Implement `POST /instructions/{instructionId}/regenerate`
- Implement `GET /tasks/{taskId}`
- Enforce selection validation and `client_request_id` idempotency
- Persist provenance metadata

Acceptance:
- First request `202`, replay `200` with same task
- `SUCCEEDED/FAILED` task payload semantics align to contract

---

# TASK 11 — Screenshot Extraction Async + Task Polling

Goal:
- Implement `POST /jobs/{jobId}/screenshots/extract`
- Implement `GET /screenshot-tasks/{taskId}`
- Enforce canonical extraction-key idempotency

Acceptance:
- Extraction accepted as async (`202`)
- Replay returns existing task/result

---

# TASK 12 — Anchor Lifecycle (Create/List/Get)

Goal:
- Implement:
  - `POST /instructions/{instructionId}/anchors`
  - `GET /instructions/{instructionId}/anchors`
  - `GET /anchors/{anchorId}`
- Support `block_id` primary and `char_range` fallback addressing
- Persist cross-version resolution metadata

Acceptance:
- Anchors are version/address aware
- Listing and retrieval follow contract filters

---

# TASK 13 — Screenshot Asset Lifecycle (Replace/Delete/Upload/Attach)

Goal:
- Implement:
  - `POST /anchors/{anchorId}/replace`
  - `DELETE /anchors/{anchorId}/assets/{assetId}`
  - `POST /jobs/{jobId}/screenshots/uploads`
  - `POST /jobs/{jobId}/screenshots/uploads/{uploadId}/confirm`
  - `POST /anchors/{anchorId}/attach-upload`
- Enforce asset version linkage and deterministic active fallback

Acceptance:
- Replace/delete/upload/attach behave per contract
- No mutable overwrite of immutable raw artifacts

---

# TASK 14 — Annotation Operation Log + Deterministic Render

Goal:
- Implement `POST /anchors/{anchorId}/annotations`
- Validate operation schema
- Compute deterministic `ops_hash` and rendered asset linkage
- Enforce idempotency and rollback on render failure

Acceptance:
- Identical annotation payloads are replay-safe
- Failed render does not leave partial state

---

# TASK 15 — Export Determinism + Status + Download URL Policy

Goal:
- Implement `POST /jobs/{jobId}/exports`
- Implement `GET /exports/{exportId}`
- Enforce deterministic identity key and provenance freeze on `SUCCEEDED`
- Ensure signed download URL appears only for `SUCCEEDED`
- Transition job to `DONE` after first successful export

Acceptance:
- Export status in `REQUESTED|RUNNING|SUCCEEDED|FAILED`
- Idempotent replay returns existing export without duplicate business audit events
- `download_url` policy and TTL behavior match contract

---

# TASK 16 — End-to-End + High-Risk Test Gate

Goal:
- Implement and enable:
  - Contract smoke tests
  - FSM unit tests
  - Callback idempotency/order tests
  - Golden path E2E mock test
  - High-risk endpoint matrix execution path

Acceptance:
- `make lint` passes
- `make test` passes
- `make check` passes
- Summary includes: what changed, why, and how verified
