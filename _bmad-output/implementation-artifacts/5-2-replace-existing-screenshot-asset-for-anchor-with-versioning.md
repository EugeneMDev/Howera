# Story 5.2: Replace Existing Screenshot Asset for Anchor with Versioning

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to replace an existing screenshot asset using updated timestamp and or offset,
so that anchor visuals can be corrected without losing traceability.

## Acceptance Criteria

1. Given valid replacement request for an owned anchor, when replacement is accepted, then replacement is processed async (`202` with `task_id`) and dedupe policy applies using canonical extraction key.
2. Given replacement completes, when versioning updates are persisted, then anchor `active_asset_id` points to new asset version, asset version increments, and `previous_asset_id` links to prior active asset.
3. Given replacement request matches current active canonical extraction key, when processed, then operation is idempotent and no new asset version is created.

## Tasks / Subtasks

- [x] Implement screenshot replacement contract and route/service boundary (AC: 1, 2, 3)
- [x] Add `ScreenshotReplaceRequest` schema aligned to OpenAPI contract fields and defaults.
- [x] Implement `POST /anchors/{anchorId}/replace` as a thin route handler with service-bound logic.
- [x] Return `202` for first accepted replacement and `200` for replay without duplicate work.
- [x] Keep response set contract-safe (`200`, `202`, `400`, `404`) and return `ScreenshotTask` payload.
- [x] Validate `instruction_version_id` against owned anchor/instruction context and reject mismatches without side effects.
- [x] Implement canonical idempotency and replay behavior for replace operations (AC: 1, 3)
- [x] Reuse canonical extraction key pattern (`job_id + instruction_version_id + timestamp_ms + offset_ms + strategy + format`) for replace dedupe.
- [x] Enforce idempotency-key replay semantics and reject mismatched duplicate idempotency payloads with `400 VALIDATION_ERROR`.
- [x] Ensure canonical replay returns existing task/result and does not increment write counters or create new tasks.
- [x] Implement asset version-chain persistence and active pointer update semantics (AC: 2, 3)
- [x] Persist screenshot asset version metadata including `version`, `previous_asset_id`, and canonical extraction linkage.
- [x] On successful replacement completion, create a new asset version, set anchor `active_asset_id` to new asset, and preserve prior active as `previous_asset_id`.
- [x] If replacement request canonical key equals current active extraction key, return idempotent replay/no-op with no new asset version.
- [x] Preserve owner scope and no-existence-leak behavior for replace submit and replacement task polling.
- [x] Add AC-mapped API/unit/OpenAPI coverage (AC: 1, 2, 3)
- [x] Add API tests for first replace accept (`202`) and replay (`200`) without duplicate task/asset writes.
- [x] Add API tests for replace completion versioning linkage (`active_asset_id`, incremented version, `previous_asset_id`).
- [x] Add API tests for canonical-equal no-op behavior (no new asset version).
- [x] Add API tests for invalid payload (`400`) and unknown/non-owned anchor no-leak `404`.
- [x] Add API tests for replace-created task polling via `GET /screenshot-tasks/{taskId}` including `operation=replace` and no-leak `404` behavior.
- [x] Add unit tests for replace canonical key behavior, version increment rules, and owner-scoped lookups.
- [x] Re-verify `/openapi.json` includes `/anchors/{anchorId}/replace` with expected request/response schema refs.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

## Dev Notes

### Developer Context Section

- Story 5.1 established screenshot extraction submit/poll foundations, deterministic canonical idempotency keys, and owner-scoped no-leak semantics.
- Story 5.2 extends the same async task contract to anchor asset replacement while adding strict asset version-chain and active-pointer behavior.
- Contract-first alignment is mandatory: replacement request/response schemas and status codes must exactly match `spec/api/openapi.yaml`.

### Technical Requirements

- Endpoint in scope:
- `POST /anchors/{anchorId}/replace`
- Contract behavior from OpenAPI:
- `200`: idempotent replay; existing replacement task returned.
- `202`: replacement task created.
- `400`: invalid replacement payload.
- `404`: no-leak for missing/non-owned anchor.
- Request model in scope:
- `ScreenshotReplaceRequest` required fields: `instruction_version_id`, `timestamp_ms`.
- Optional fields: `offset_ms`, `strategy`, `format`, `idempotency_key`.
- Validation guardrail:
- `instruction_version_id` must be validated against the owned anchor's instruction context; mismatches must be rejected with contract-safe error behavior and no state mutation.
- Response model:
- `ScreenshotTask` with `operation=replace` and task state in `PENDING|RUNNING|SUCCEEDED|FAILED`.
- Versioning expectations:
- On replace success, new screenshot asset version is linked with `previous_asset_id` to prior active asset.
- Anchor `active_asset_id` must move to the new asset version.
- Idempotent match to current active canonical extraction key must not create a new asset version.

### Architecture Compliance

- `spec/` is read-only source of truth.
- Keep business logic out of routes; enforce replace ownership/idempotency/versioning in service and repository layers.
- Preserve no-existence-leak policy (`404`) for unauthorized or missing resources.
- Preserve artifact discipline:
- raw artifacts remain immutable.
- derived screenshot assets are versioned and linked (`previous_asset_id`, active pointer management).
- Maintain secure logging boundaries and sanitized failure messaging.

### Library & Framework Requirements

- FastAPI + Pydantic models remain contract authority at runtime.
- Reuse existing screenshot task patterns (`ScreenshotTask`, write-counter assertions, no-side-effect replay checks).
- Reuse existing deterministic in-memory persistence conventions and helper methods in `InMemoryStore`.
- No new dependencies expected.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/schemas/job.py` (add `ScreenshotReplaceRequest`; extend screenshot asset metadata models only if required by route/service contracts)
- `apps/api/app/routes/jobs.py` (add `POST /anchors/{anchorId}/replace`)
- `apps/api/app/services/jobs.py` (add replace request service boundary and replay semantics)
- `apps/api/app/repositories/memory.py` (replace task creation, canonical mapping, asset version linkage, anchor active pointer state)
- `apps/api/app/main.py` (OpenAPI response-code allowlist, request-validation mapping, contract schema shaping for replace path)
- `apps/api/tests/test_jobs_ownership.py` (replace API and repository/service behavior tests)
- `apps/api/tests/test_auth_middleware.py` (OpenAPI contract assertions for replace path and schema refs)

### Testing Requirements

- Validate first replacement request returns `202` and replay returns `200` with same `task_id`.
- Validate canonical duplicate requests are idempotent and do not create new tasks or increment screenshot write counters.
- Validate duplicate idempotency key with mismatched payload returns `400 VALIDATION_ERROR` with no mutation.
- Validate replace success updates version chain:
- anchor `active_asset_id` points to new asset.
- new asset version increments from prior active.
- new asset `previous_asset_id` points to prior active asset.
- Validate canonical request equal to current active extraction key returns idempotent no-op without creating a new asset version.
- Validate unknown/non-owned anchor returns no-leak `404 RESOURCE_NOT_FOUND`.
- Validate invalid replacement payload returns `400` and preserves state.
- Validate owned replace-created task polling via `GET /screenshot-tasks/{taskId}` returns `operation=replace`, and unknown/non-owned task polling remains no-leak `404`.
- Validate `instruction_version_id`/anchor context mismatch is rejected with contract-safe error handling and no write-side effects.
- Validate `/openapi.json` contract alignment for `/anchors/{anchorId}/replace` request body and `200/202/400/404` response schemas.
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Story 5.1 introduced:
- canonical extraction key generation helper and replay behavior.
- owner-scoped screenshot task retrieval and no-leak boundaries.
- screenshot task write-counter assertions to catch side-effect regressions.
- Story 5.1 review corrections hardened replay semantics and version-id validation; carry the same strictness into replace flow.
- Reuse existing screenshot extraction task/result patterns to avoid parallel ad hoc task models.

### Git Intelligence Summary

- Recent backend work consistently uses:
- thin route handlers and service-owned business decisions.
- deterministic repository updates with explicit replay/no-op handling.
- OpenAPI shaping in `app/main.py` plus schema/response assertions in `test_auth_middleware.py`.
- explicit no-side-effect and ownership tests in `test_jobs_ownership.py`.
- Keep Story 5.2 implementation as a minimal diff extension of these patterns.

### Project Structure Notes

- No separate architecture artifact exists in `_bmad-output/planning-artifacts/`; rely on `epics.md`, `prd.md`, OpenAPI, and current screenshot extraction implementation as guardrails.
- Keep Story 5.2 scoped to replace behavior only; delete/upload/attach/annotation endpoints belong to later Epic 5 stories.

### References

- `spec/api/openapi.yaml` (`ScreenshotReplaceRequest`, `ScreenshotTask`, `ScreenshotAsset`, `ScreenshotAnchor`, `/anchors/{anchorId}/replace`)
- `_bmad-output/planning-artifacts/epics.md` (Epic 5, Story 5.2)
- `_bmad-output/planning-artifacts/prd.md` (FR-033 and screenshot lifecycle constraints)
- `spec/acceptance/tasks_codex_v1.md` (Task 13 replace lifecycle intent)
- `_bmad-output/project-context.md` (contract-first, idempotent async processing, artifact versioning, no-leak boundaries)
- `_bmad-output/implementation-artifacts/5-1-extract-screenshot-with-alignment-parameters-and-anchor-metadata.md`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/schemas/job.py`
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
- `_bmad-output/implementation-artifacts/5-1-extract-screenshot-with-alignment-parameters-and-anchor-metadata.md`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/schemas/job.py`
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_auth_middleware.py`

### Completion Notes List

- 2026-03-01: Created Story 5.2 artifact with AC-mapped tasks, replace/versioning constraints, and implementation guardrails.
- 2026-03-01: Captured canonical dedupe and idempotency expectations for replacement requests, including canonical-equal no-op behavior.
- 2026-03-01: Captured asset version-chain requirements (`active_asset_id`, incremented version, `previous_asset_id`) for deterministic traceability.
- 2026-03-01: Ultimate context engine analysis completed - comprehensive developer guide created.
- 2026-03-01: Implemented `POST /anchors/{anchorId}/replace` with owner-scoped no-leak behavior, instruction-version context validation, and contract-safe `200/202/400/404` semantics.
- 2026-03-01: Added replace-task idempotency with canonical extraction key + idempotency-key replay handling, including canonical-equal active-asset no-op behavior.
- 2026-03-01: Added screenshot anchor/asset version-chain persistence (`version`, `previous_asset_id`, `active_asset_id`) and replace task polling assertions.
- 2026-03-01: Verified with `make lint`, `make test`, and `make check` in `apps/api` (all passing).

### File List

- `_bmad-output/implementation-artifacts/5-2-replace-existing-screenshot-asset-for-anchor-with-versioning.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/schemas/job.py`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_jobs_ownership.py`

### Change Log

- 2026-03-01: Created Story 5.2 artifact and moved sprint status from `backlog` to `ready-for-dev`.
- 2026-03-01: Implemented screenshot replace API/service/repository flow with canonical/idempotent replay and anchor asset version chaining.
- 2026-03-01: Added OpenAPI contract shaping and validation-path mapping for `/anchors/{anchorId}/replace`.
- 2026-03-01: Added API and unit coverage for replace accept/replay, idempotency mismatch, no-leak ownership, canonical no-op, and version-chain persistence.
- 2026-03-01: Ran `make lint`, `make test`, and `make check` in `apps/api`; moved story to `review`.
- 2026-03-01: Senior Developer Review completed; verified replace replay/version-chain behavior and moved story to `done`.

## Senior Developer Review (AI)

### Outcome

- Approved.
- No remaining HIGH or MEDIUM issues after review and verification.

### Key Validation Notes

- Confirmed replace canonical replay does not stale-replay historical succeeded tasks after anchor active key changes.
- Confirmed version-chain semantics remain intact (`active_asset_id`, incremented `version`, `previous_asset_id`).
- Confirmed contract-safe behavior and response set for `/anchors/{anchorId}/replace` remains aligned to OpenAPI.

### Verification Evidence

- `make check` in `apps/api` passed on 2026-03-01 (`lint` + `test`, 150 tests total).
