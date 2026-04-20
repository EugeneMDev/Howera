# Story 5.1: Extract Screenshot with Alignment Parameters and Anchor Metadata

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to request screenshot extraction at a timestamp with optional alignment parameters,
so that I can insert precise visual evidence into instructions.

## Acceptance Criteria

1. Given a valid extraction request with ownership-validated job and instruction context, when extraction is submitted, then API accepts extraction as async (`202`) with `task_id` and request stores an idempotency key or dedupe token.
2. Given a duplicate extraction request (same canonical extraction key: `job_id + instruction_version + timestamp_ms + offset_ms + strategy + format`), when processed, then existing task or result is returned and duplicate extraction work is not created.
3. Given extraction completes, when result is persisted, then anchor and asset metadata includes `asset_id`, `image_uri`, dimensions, and extraction parameters, and ownership scope is enforced in retrieval.

## Tasks / Subtasks

- [x] Implement screenshot extraction task contract and route/service boundary (AC: 1, 2)
- [x] Add schema models for screenshot extraction request/task payloads aligned to contract (`ScreenshotExtractionRequest`, `ScreenshotTask`).
- [x] Implement `POST /jobs/{jobId}/screenshots/extract` with thin route + service-bound ownership and validation behavior.
- [x] Implement `GET /screenshot-tasks/{taskId}` polling route with owner-scoped no-leak `404` behavior.
- [x] Keep response set contract-safe (`200`, `202`, `400`, `404`) for extraction and (`200`, `404`) for task polling.
- [x] Implement canonical idempotency and dedupe semantics (AC: 1, 2)
- [x] Persist deterministic canonical extraction key using `job_id + instruction_version_id + timestamp_ms + offset_ms + strategy + format`.
- [x] Support `idempotency_key` replay semantics where provided and prevent duplicate extraction work creation.
- [x] Return existing task/result on duplicate canonical request (`200`) and create task on first accept (`202`).
- [x] Implement persisted extraction outcome linkage for anchor/asset metadata (AC: 3)
- [x] Persist task lifecycle states (`PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`) and safe failure metadata fields.
- [x] On success, persist or link anchor/asset references so downstream retrieval paths surface `asset_id`, `image_uri`, `width`, `height`, and extraction parameters.
- [x] Enforce ownership scope and no-leak policy for extraction submission and screenshot-task polling/read paths.
- [x] Add AC-mapped API/unit coverage and OpenAPI checks (AC: 1, 2, 3)
- [x] Add API tests for first extraction accept (`202`) and duplicate replay (`200`) without duplicate writes.
- [x] Add API tests for task polling success and unknown/non-owned no-leak `404`.
- [x] Add API tests for invalid extraction payload (`400`) and side-effect-free reject behavior.
- [x] Add unit tests for canonical key generation, idempotency behavior, owner scoping, and read-only polling semantics.
- [x] Re-verify `/openapi.json` includes `/jobs/{jobId}/screenshots/extract` and `/screenshot-tasks/{taskId}` with expected response codes/schema refs.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

## Dev Notes

### Developer Context Section

- Epic 5 begins screenshot and anchor lifecycle implementation; Story 5.1 is the extraction entrypoint and async polling foundation.
- Story 5.1 should mirror established Epic 4 async patterns: thin routes, service-bound ownership/no-leak checks, and deterministic idempotency semantics.
- Contract-first alignment is critical: extraction and polling response sets and schemas must match OpenAPI exactly to avoid drift.

### Technical Requirements

- Endpoints in scope:
  - `POST /jobs/{jobId}/screenshots/extract`
  - `GET /screenshot-tasks/{taskId}`
- Contract behavior from OpenAPI:
  - extraction `POST`:
    - `200`: idempotent replay; existing extraction task returned.
    - `202`: extraction task created.
    - `400`: invalid extraction payload.
    - `404`: no-leak for missing/non-owned job/instruction context.
  - task polling `GET`:
    - `200`: `ScreenshotTask`.
    - `404`: no-leak for missing/non-owned task.
- Canonical dedupe key (contract description): `job_id + instruction_version_id + timestamp_ms + offset_ms + strategy + format`.
- Request fields:
  - required: `instruction_id`, `instruction_version_id`, `timestamp_ms`
  - optional: `anchor_id`, `block_id`, `char_range`, `offset_ms`, `strategy`, `format`, `idempotency_key`
- Task fields:
  - required: `task_id`, `operation`, `status`
  - optional outcome fields: `anchor_id`, `asset_id`, `failure_code`, `failure_message`

### Architecture Compliance

- `spec/` is read-only source of truth.
- Keep business logic out of routes; enforce ownership, idempotency, and dedupe in service/repository boundaries.
- Preserve no-existence-leak policy for editor-facing resources (`404` indistinguishable for unauthorized/missing).
- Preserve artifact discipline:
  - raw artifacts remain immutable
  - derived screenshot assets are versioned/linked through anchor metadata.
- Maintain secure logging boundaries (no secrets or sensitive payload values in logs/failure messages).

### Library & Framework Requirements

- FastAPI + Pydantic contracts remain authoritative.
- Reuse existing API error shape patterns (`Error`, `NoLeakNotFoundError`).
- Reuse deterministic in-memory repository patterns already established for run/retry/regenerate idempotency flows.
- No new dependencies expected.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/schemas/` (add screenshot extraction/task schemas; module placement consistent with existing schema organization)
- `apps/api/app/routes/jobs.py` (add extraction + task polling handlers)
- `apps/api/app/services/jobs.py` (add extraction submit/poll service boundary and idempotency behavior)
- `apps/api/app/repositories/memory.py` (persist screenshot tasks, canonical key index, owner-scoped lookup)
- `apps/api/app/main.py` (OpenAPI response-set shaping/contract-safe schema refs as needed)
- `apps/api/tests/test_jobs_ownership.py` (API/service tests for extraction + polling idempotency/no-leak behavior)
- `apps/api/tests/test_auth_middleware.py` (OpenAPI contract assertions for new screenshot paths)

### Testing Requirements

- Validate extraction first-call success returns `202` with contract task payload.
- Validate duplicate canonical extraction request returns `200` replay without duplicate task writes.
- Validate invalid extraction payload returns contract `400` and does not mutate task/job state.
- Validate extraction and polling enforce owner scope and no-leak `404`.
- Validate task polling remains read-only and does not mutate unrelated state.
- Validate `/openapi.json` includes:
  - `/jobs/{jobId}/screenshots/extract` with `200/202/400/404`
  - `/screenshot-tasks/{taskId}` with `200/404`
  - schema refs to `ScreenshotExtractionRequest`, `ScreenshotTask`, and `NoLeakNotFoundError`.
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Epic 4 finished with robust idempotent async task patterns (`POST` create/replay + `GET` poll), owner-scoped reads, and explicit no-leak test coverage.
- Existing suite already uses deterministic write counters and side-effect assertions for reject/read paths; apply the same approach for screenshot tasks.
- Prior reviews repeatedly surfaced OpenAPI/runtime drift risks; include explicit OpenAPI assertions for screenshot extraction and polling paths.

### Git Intelligence Summary

- Current backend patterns favor:
- thin route handlers with service-bound domain logic
- deterministic in-memory persistence and owner-scoped lookup helpers
- explicit no-side-effect assertions in tests for reject and read-only flows
- response code/schema shaping in `app/main.py` plus OpenAPI assertions in `test_auth_middleware.py`
- Story 5.1 should extend these patterns with minimal diff and no unrelated refactors.

### Project Structure Notes

- No standalone architecture artifact exists in `_bmad-output/planning-artifacts/`; use `epics.md`, `prd.md`, OpenAPI, and recent Story 4.x implementation patterns as guardrails.
- Keep scope focused on extraction submit + task polling foundations for Epic 5.1; replacement/delete/upload/annotation operations are handled by later stories.

### References

- `spec/api/openapi.yaml` (`ScreenshotExtractionRequest`, `ScreenshotTask`, `/jobs/{jobId}/screenshots/extract`, `/screenshot-tasks/{taskId}`)
- `_bmad-output/planning-artifacts/epics.md` (Epic 5, Story 5.1)
- `_bmad-output/planning-artifacts/prd.md` (FR-022, FR-023, FR-024, contract-first constraints)
- `spec/acceptance/tasks_codex_v1.md` (Task 11 extraction + screenshot-task polling intent)
- `_bmad-output/project-context.md` (idempotent async model, artifact discipline, no-leak boundaries)
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_auth_middleware.py`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `spec/api/openapi.yaml`
- `spec/acceptance/tasks_codex_v1.md`
- `_bmad-output/project-context.md`

### Completion Notes List

- 2026-03-01: Created Story 5.1 artifact with screenshot extraction + polling requirements, AC-mapped tasks, and implementation guardrails.
- 2026-03-01: Captured canonical extraction idempotency semantics and no-leak ownership boundaries for extraction and task polling paths.
- 2026-03-01: Incorporated continuity guardrails from Epic 4 async idempotent task patterns and contract-shaping/openapi test practices.
- 2026-03-01: Ultimate context engine analysis completed - comprehensive developer guide created.
- 2026-03-01: Implemented screenshot extraction contract models, routes, service logic, and deterministic in-memory dedupe/idempotency persistence.
- 2026-03-01: Added screenshot task polling with owner-scoped no-leak `404` behavior and persisted success linkage for anchor/asset metadata.
- 2026-03-01: Updated OpenAPI shaping and validation remap for extraction (`400 VALIDATION_ERROR`) and added explicit OpenAPI assertions.
- 2026-03-01: Verified with `make lint`, `make test`, and `make check` in `apps/api` (all passing).
- 2026-03-01: Addressed code review findings by enforcing `instruction_version_id` validation, hardening canonical/idempotency-key replay behavior, and adding owner-scoped screenshot asset retrieval helpers.
- 2026-03-01: Added regression coverage for invalid `instruction_version_id`, canonical replay with a new idempotency key, and owner-scoped screenshot asset metadata reads.

### File List

- `_bmad-output/implementation-artifacts/5-1-extract-screenshot-with-alignment-parameters-and-anchor-metadata.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/main.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/routes/instructions.py`
- `apps/api/app/domain/instruction_validation.py`
- `apps/api/app/schemas/instruction.py`
- `apps/api/app/schemas/job.py`
- `apps/api/app/services/instructions.py`
- `apps/api/app/services/jobs.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_instructions_ownership.py`
- `apps/api/tests/test_jobs_ownership.py`

### Change Log

- 2026-03-01: Created Story 5.1 artifact and moved sprint status from `backlog` to `ready-for-dev`.
- 2026-03-01: Implemented Story 5.1 screenshot extraction submit/polling flow with canonical/idempotent dedupe semantics, owner-scoped no-leak behavior, persisted anchor/asset linkage, and AC-mapped API/unit/OpenAPI test coverage.
- 2026-03-01: Resolved code-review findings for instruction version context validation, idempotency replay consistency, and owner-scoped screenshot asset retrieval coverage.
