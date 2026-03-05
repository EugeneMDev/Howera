# Story 6.1: Create Export Request Bound to Exact Instruction Version

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to request export for a specific instruction version,
so that generated artifacts are reproducible and non-ambiguous.

## Acceptance Criteria

1. Given an authenticated editor with owned job and explicit `instruction_version_id`, when export request is submitted with format, then export identity key is computed as `instruction_version_id + format + screenshot_set_hash`, and request is idempotent on that identity key.
2. Given same identity key is requested again, when request is processed, then existing `export_id` and current export state are returned, and no duplicate export record or workflow is created.
3. Given missing or invalid version or unsupported format, when request is submitted, then API returns contract-defined validation error, and no export record is created.

## Tasks / Subtasks

- [x] Implement export request contract models and route/service boundary (AC: 1, 2, 3)
- [x] Add request/response schemas aligned to OpenAPI for this story scope: `CreateExportRequest`, `ExportFormat`, `ExportStatus`, `Export`, `ExportProvenance`, `ExportAnchorBinding`, `ExportAuditEventType`.
- [x] Implement `POST /jobs/{jobId}/exports` as thin route handler with service-owned ownership/no-leak behavior and `200/202/400/404` response set.
- [x] Preserve contract-safe error code for invalid request inputs: `EXPORT_REQUEST_INVALID` with no write-side effects.
- [x] Implement deterministic export identity-key and idempotent replay behavior (AC: 1, 2)
- [x] Compute `screenshot_set_hash` deterministically from the scoped anchor set used for the requested `instruction_version_id` (stable ordering and canonical payload serialization).
- [x] Compute identity key deterministically as `instruction_version_id + format + screenshot_set_hash`.
- [x] Persist lookup index keyed by deterministic identity so replay returns existing export record with `200` and does not create duplicate workflow work.
- [x] Ensure initial accepted request returns `202` with export status `REQUESTED`.
- [x] Implement validation and no-mutation reject paths (AC: 3)
- [x] Reject missing or unknown `instruction_version_id` for the owned job as `400 EXPORT_REQUEST_INVALID`.
- [x] Reject invalid payload shape/enum inputs with contract-safe `400` handling (no fallback `422` leaks for this endpoint).
- [x] Preserve ownership no-leak behavior (`404`) for unknown/cross-owner job IDs.
- [x] Add persistence primitives for export request lifecycle seed data (AC: 1, 2)
- [x] Add in-memory export records and deterministic replay index without reusing single-dispatch-per-job maps used by run/retry.
- [x] Seed export record with required contract fields (`id`, `job_id`, `format`, `status`, `instruction_version_id`, `identity_key`, `screenshot_set_hash`, `created_at`, `updated_at`).
- [x] Seed minimal provenance scaffold required by contract surface without freezing semantics (freeze is Story 6.3).
- [x] Add AC-mapped API/unit/OpenAPI coverage (AC: 1, 2, 3)
- [x] Add API tests for first request (`202`) and replay (`200`) proving no duplicate export record/workflow side effects.
- [x] Add API tests for invalid/missing version and unsupported format returning `400` with `EXPORT_REQUEST_INVALID` and no mutation.
- [x] Add API tests for cross-owner/missing job no-leak `404`.
- [x] Add unit tests for deterministic `screenshot_set_hash` and identity-key stability across equivalent anchor ordering.
- [x] Re-verify `/openapi.json` includes `/jobs/{jobId}/exports` with expected request/response schema refs and `200/202/400/404`.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

## Dev Notes

### Developer Context Section

- Epic 6 starts the export domain. Story 6.1 establishes deterministic export request identity and idempotent replay boundaries; status retrieval/download URL/freeze/audit progression is completed by later stories in Epic 6.
- Existing implementation already uses deterministic replay patterns (`run`, `retry`, screenshot extract/replace/annotate). Reuse those patterns for behavior consistency and testability.
- Contract-first scope remains strict: do not add endpoints/status codes/schema fields beyond `spec/api/openapi.yaml`.

### Technical Requirements

- Endpoint in scope:
- `POST /jobs/{jobId}/exports`
- Contract behavior from OpenAPI:
- `200`: idempotent replay; existing `Export` returned.
- `202`: export requested; `Export` returned.
- `400`: `Error` with `EXPORT_REQUEST_INVALID` for invalid version/format/inputs.
- `404`: no-leak `NoLeakNotFoundError` for unauthorized/missing job.
- Request schema requirements:
- `CreateExportRequest` requires `format` and `instruction_version_id`; optional `idempotency_key`.
- `format` enum is `PDF|MD_ZIP`.
- Response schema requirements:
- `Export` includes required fields `id`, `job_id`, `format`, `status`, `instruction_version_id`, `identity_key`, `screenshot_set_hash`, `created_at`, `updated_at`.
- Determinism/idempotency requirements:
- Identity key must be computed from `instruction_version_id + format + screenshot_set_hash`.
- Duplicate requests for same identity key must return the same `export_id`/state and must not create duplicate workflow work.

### Architecture Compliance

- `spec/` is read-only source of truth.
- Keep route handlers thin; implement ownership checks, identity-key generation, replay logic, and validation in service/repository layers.
- Preserve no-existence-leak behavior (`404`) for unauthorized/missing job access.
- Maintain deterministic/idempotent async safety: accepted replay must be side-effect free.
- Preserve artifact discipline: exports remain explicit linked artifacts in job manifest/history; do not overwrite immutable raw artifacts.
- Respect FSM discipline on job lifecycle updates; this story should not bypass `ensure_transition` if job status changes are introduced.

### Library & Framework Requirements

- FastAPI + Pydantic remain request/response contract authority.
- Reuse existing repository/service patterns already used by `run`, `retry`, and screenshot idempotency maps.
- Reuse OpenAPI shaping and response-code allowlisting patterns in `app/main.py` and assertions in `test_auth_middleware.py`.
- No new dependencies expected.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/schemas/job.py` (export request/response enums and models)
- `apps/api/app/routes/jobs.py` (add `POST /jobs/{jobId}/exports`)
- `apps/api/app/services/jobs.py` (export request orchestration, ownership/no-leak behavior, deterministic replay handling)
- `apps/api/app/repositories/memory.py` (export record persistence, identity-key index, deterministic screenshot hash computation)
- `apps/api/app/main.py` (OpenAPI response-code allowlist, export schema shaping, request-validation-path mapping for `400`)
- `apps/api/tests/test_jobs_ownership.py` (API + unit coverage for export request determinism and reject/no-mutation paths)
- `apps/api/tests/test_auth_middleware.py` (OpenAPI path/schema assertions for export create endpoint)

### Testing Requirements

- Validate first create-export request returns `202` with contract-required `Export` fields.
- Validate same deterministic identity replay returns `200`, same `export_id`, and no duplicate write/dispatch side effects.
- Validate missing/invalid `instruction_version_id` and unsupported format return `400` (`EXPORT_REQUEST_INVALID`) with no export record created.
- Validate cross-owner/missing job requests return no-leak `404`.
- Validate deterministic `screenshot_set_hash` and identity-key stability with sorted/canonical anchor input.
- Validate `/openapi.json` includes `/api/v1/jobs/{jobId}/exports` with request ref `CreateExportRequest`, response ref `Export`, and response codes `200/202/400/404`.
- Final verification gate: `make lint`, `make test`, `make check` in `apps/api`.

### Previous Story Intelligence

- Story 5.6 enforced semantic validation and deterministic anchor/asset reference behavior, which is a prerequisite for stable export input hashing.
- Stories 5.1-5.5 established ownership-scoped no-leak handling, idempotent replay maps, and rollback/no-partial-state patterns; export request flow should follow the same discipline.
- Existing route/service boundaries favor thin routes and repository-contained deterministic state transitions.

### Git Intelligence Summary

- Recent history (`5-6`, `4-3`, `3-4`) continues a minimal-diff, contract-first style with explicit OpenAPI assertions and no-leak behavior enforcement.
- Tests are extended in-place rather than replaced; follow that pattern for export request coverage.

### Project Structure Notes

- No standalone architecture artifact is present in planning outputs; use OpenAPI, PRD, Epic 6 decomposition, and current code patterns as primary implementation guardrails.
- Keep this story scoped to export request determinism/idempotency. Export lifecycle progression, provenance freeze, status retrieval, download URL policy, and canonical audit events are handled by Stories 6.2-6.6.

### References

- `spec/api/openapi.yaml` (`CreateExportRequest`, `ExportFormat`, `Export`, `/jobs/{jobId}/exports`)
- `_bmad-output/planning-artifacts/epics.md` (Epic 6, Story 6.1)
- `_bmad-output/planning-artifacts/prd.md` (FR-025, FR-039, FR-040, FR-044; idempotency/export determinism requirements)
- `spec/acceptance/tasks_codex_v1.md` (Task 15 export determinism baseline)
- `_bmad-output/project-context.md` (contract-first, idempotency, artifact discipline, no-leak policy)
- `_bmad-output/implementation-artifacts/5-6-anchor-addressing-persistence-policy-and-cross-version-traceability.md`
- `apps/api/app/main.py`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_jobs_ownership.py`

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
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/main.py`

### Completion Notes List

- 2026-03-03: Created Story 6.1 artifact with AC-mapped tasks for deterministic export identity-key generation, idempotent replay, and contract-safe validation/no-leak behavior.
- 2026-03-03: Captured endpoint/schema/response guardrails from OpenAPI and project invariants from AGENTS/project-context for implementation readiness.
- 2026-03-04: Implemented export request contract models and `POST /jobs/{jobId}/exports` with deterministic identity key (`instruction_version_id|format|screenshot_set_hash`) and replay-safe `200`/first `202` behavior.
- 2026-03-04: Added in-memory export persistence primitives (`ExportRecord`, identity index, deterministic screenshot-set hashing, provenance scaffold seeding) without duplicate export record creation on replay.
- 2026-03-04: Added export endpoint OpenAPI response-code/schema shaping and request-validation mapping to `400 EXPORT_REQUEST_INVALID` for malformed/unsupported payloads.
- 2026-03-04: Added API and unit coverage for export create replay semantics, invalid-input no-mutation behavior, no-leak ownership checks, and deterministic hash/identity stability.
- 2026-03-04: Verification passed in `apps/api` via `make lint`, `make test`, and `make check` (`178` tests).
- 2026-03-04: Addressed code-review findings by rejecting `idempotency_key: null`, rejecting ambiguous job+version instruction matches, and aligning export OpenAPI schema nullability; expanded regression coverage and re-verified (`179` tests).

### File List

- `_bmad-output/implementation-artifacts/6-1-create-export-request-bound-to-exact-instruction-version.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/schemas/job.py`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_jobs_ownership.py`

### Change Log

- 2026-03-03: Created Story 6.1 artifact and moved sprint status from `backlog` to `ready-for-dev`; updated `epic-6` from `backlog` to `in-progress`.
- 2026-03-04: Implemented Story 6.1 export request determinism and idempotent replay (`POST /jobs/{jobId}/exports`) with contract-safe validation and OpenAPI alignment.
- 2026-03-04: Added AC-mapped API/unit tests and completed verification gates (`make lint`, `make test`, `make check`); moved story status to `review`.
- 2026-03-04: Completed code-review remediation for contract/nullability and ambiguous instruction-version binding; reran `make lint`, `make test`, and `make check`; moved story status to `done`.

## Senior Developer Review (AI)

### Reviewer

GPT-5.3-Codex

### Date

2026-03-04

### Outcome

Approved after fixes.

### Findings Addressed

- Enforced contract-safe rejection for `idempotency_key: null` on `POST /jobs/{jobId}/exports` (`400 EXPORT_REQUEST_INVALID`).
- Rejected ambiguous instruction selection when multiple instructions share the same owned `job_id + version`, preventing silent provenance/hash drift.
- Aligned OpenAPI export schema for `provenance_frozen_at` to contract shape (`type: string`, `format: date-time`).
- Added regression tests covering all above cases.

### Verification

- `cd apps/api && HOWERA_CALLBACK_SECRET=test-secret make lint`
- `cd apps/api && HOWERA_CALLBACK_SECRET=test-secret make test` (`179` tests)
- `cd apps/api && HOWERA_CALLBACK_SECRET=test-secret make check`
