# Story 6.4: Retrieve Export Status by Export ID

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to query export status by export ID,
so that I can track asynchronous export progress.

## Acceptance Criteria

1. Given owned `export_id`, when status is requested, then response includes export FSM state, `export_id`, identity key, and provenance summary fields.
2. Given unknown or unauthorized export ID, when status is requested, then no-existence-leak policy is applied (`404`).

## Tasks / Subtasks

- [x] Implement owner-scoped export status retrieval endpoint (AC: 1, 2)
- [x] Add `GET /exports/{exportId}` route with `200` `Export` and `404` `NoLeakNotFoundError` contract behavior.
- [x] Add service-layer read method that resolves export by owner and export ID without side effects.
- [x] Reuse repository owner-scope lookup semantics and preserve no-existence-leak behavior for cross-owner and missing IDs.
- [x] Enforce contract-safe export response semantics (AC: 1)
- [x] Ensure response includes export state, `id`, `identity_key`, and provenance summary fields per OpenAPI `Export`.
- [x] Ensure `download_url` and `download_url_expires_at` are returned only when export state is `SUCCEEDED`.
- [x] Ensure status polling is read-only and does not mutate export/job state or write counters.
- [x] Add AC-mapped API/unit/OpenAPI coverage (AC: 1, 2)
- [x] Add API tests for successful owned retrieval across representative export states (`REQUESTED`, `RUNNING`, `SUCCEEDED`, `FAILED`).
- [x] Add API tests for unknown and cross-owner export retrieval returning identical `404` no-leak shape.
- [x] Add tests validating download URL visibility policy (present only for `SUCCEEDED`).
- [x] Extend `/openapi.json` assertions for `/exports/{exportId}` response-code/schema alignment.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

## Dev Notes

### Developer Context Section

- Story 6.1 introduced deterministic export request identity and idempotent `POST /jobs/{jobId}/exports` behavior.
- Story 6.2 completed export provenance persistence, snapshot binding, and reference IDs needed for reproducibility.
- Story 6.3 implemented export execution lifecycle (`REQUESTED -> RUNNING -> SUCCEEDED|FAILED`) with replay safety and success freeze semantics.
- Story 6.4 is retrieval-only scope for `GET /exports/{exportId}` and should not expand signed URL issuance policy beyond contract visibility rules.

### Technical Requirements

- Endpoint in scope:
- `GET /exports/{exportId}`
- Contract behavior from OpenAPI:
- `200` returns `Export` schema.
- `404` returns `NoLeakNotFoundError` for both missing and unauthorized export IDs.
- Response semantics:
- Return export FSM state in `REQUESTED|RUNNING|SUCCEEDED|FAILED`.
- Return deterministic export identity fields and provenance summary (`identity_key`, `provenance`, `provenance_frozen_at`, `last_audit_event`).
- Ensure `download_url` is present only when export state is `SUCCEEDED`.
- Story boundaries:
- Signed URL generation policy and TTL issuance mechanics are Story 6.5.
- Canonical export audit event-stream expansion is Story 6.6.

### Architecture Compliance

- `spec/` is read-only source of truth.
- Keep route handlers thin; ownership and no-leak checks stay in service/repository.
- Maintain no-existence-leak policy for unauthorized/missing resources.
- Retrieval must be read-only and deterministic.
- Do not introduce direct SDK/provider calls in route/service layers.

### Library & Framework Requirements

- FastAPI + Pydantic are contract authority.
- Reuse current route/service/repository architecture and existing error schemas.
- Reuse OpenAPI response-shaping pattern in `app/main.py` plus contract assertions in tests.
- No new dependencies expected.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/routes/jobs.py` (add `GET /exports/{exportId}`)
- `apps/api/app/services/jobs.py` (add owner-scoped export retrieval method)
- `apps/api/app/repositories/memory.py` (reuse/adjust `get_export_for_owner` as needed)
- `apps/api/app/main.py` (OpenAPI response-code/schema shaping for `/exports/{exportId}`)
- `apps/api/tests/test_jobs_ownership.py` (API/unit retrieval/no-leak/policy coverage)
- `apps/api/tests/test_auth_middleware.py` (OpenAPI contract assertions)

### Testing Requirements

- Validate owned export retrieval returns `200` with contract fields.
- Validate missing and cross-owner retrieval return identical `404` no-leak shape.
- Validate download URL visibility policy: visible only for `SUCCEEDED`.
- Validate retrieval path causes no state mutation and no additional write counts.
- Validate `/openapi.json` includes `/exports/{exportId}` with `200` and `404` only, and correct schema refs.
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Story 6.3 deferred export status retrieval explicitly to this story and added execution helpers that now populate export state deterministically.
- Story 6.3 also established replay-safe semantics and provenance freeze behavior that 6.4 must surface correctly without mutation.
- Existing no-leak ownership patterns across jobs/instructions/transcript should be mirrored for export retrieval.

### Git Intelligence Summary

- Recent completed work follows minimal-diff, contract-first changes with explicit OpenAPI assertions and no-leak tests.
- Existing export logic is centralized in `jobs` service plus in-memory repository; keep retrieval in this pattern.
- Prefer additive tests over refactors to preserve reviewability and reduce regression risk.

### Project Structure Notes

- No standalone architecture artifact is present in `_bmad-output/planning-artifacts/`; derive constraints from OpenAPI, PRD, epics, project context, and existing implementation patterns.
- Keep Story 6.4 strictly scoped to retrieval and response-shape correctness for existing export records.
- Defer signed URL issuance and export audit event expansion to Stories 6.5 and 6.6.

### References

- `spec/api/openapi.yaml` (`/exports/{exportId}`, `Export`, `NoLeakNotFoundError`, `ExportStatus`)
- `_bmad-output/planning-artifacts/epics.md` (Epic 6, Story 6.4)
- `_bmad-output/planning-artifacts/prd.md` (FR-026, FR-027, FR-028)
- `spec/acceptance/v1_mvp.md` (Export status + download URL visibility acceptance)
- `spec/acceptance/tasks_codex_v1.md` (Task 15 export status and policy expectations)
- `_bmad-output/project-context.md` (contract-first and no-leak architecture constraints)
- `_bmad-output/implementation-artifacts/6-1-create-export-request-bound-to-exact-instruction-version.md`
- `_bmad-output/implementation-artifacts/6-2-persist-complete-export-provenance-and-snapshot-references.md`
- `_bmad-output/implementation-artifacts/6-3-execute-export-fsm-and-freeze-provenance-on-success.md`
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
- `spec/acceptance/v1_mvp.md`
- `spec/acceptance/tasks_codex_v1.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/6-3-execute-export-fsm-and-freeze-provenance-on-success.md`

### Completion Notes List

- 2026-03-04: Created Story 6.4 artifact from sprint backlog with AC-mapped tasks for owner-scoped export status retrieval and no-leak behavior.
- 2026-03-04: Captured endpoint contract and scope boundaries from OpenAPI/PRD/Epic 6 to keep implementation retrieval-only for this story.
- 2026-03-04: Incorporated prior export-story guardrails (identity determinism, provenance freeze, replay safety) so retrieval reflects current canonical state without mutation.
- 2026-03-04: Ultimate context engine analysis completed - comprehensive developer guide created.
- 2026-03-04: Implemented `GET /api/v1/exports/{exportId}` with owner-scoped no-leak `404` behavior and read-only retrieval in `JobService`.
- 2026-03-04: Enforced download URL visibility policy in status retrieval responses (download fields returned only for `SUCCEEDED`).
- 2026-03-04: Added API/OpenAPI contract coverage for export-status retrieval including state matrix, no-leak parity, and schema assertions.
- 2026-03-04: Verified quality gates in `apps/api` with `make lint`, `make test`, and `make check` (all passing).

### File List

- `_bmad-output/implementation-artifacts/6-4-retrieve-export-status-by-export-id.md`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_auth_middleware.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-04: Created Story 6.4 artifact and moved sprint status from `backlog` to `ready-for-dev`.
- 2026-03-04: Implemented export status retrieval endpoint/service contract, added AC coverage, and moved story/sprint status to `review`.
- 2026-03-04: Completed code-review with no HIGH/MEDIUM findings; moved story and sprint status to `done`.

## Senior Developer Review (AI)

### Reviewer

- `Codex` (AI Senior Developer Reviewer)
- Date: 2026-03-04

### Outcome

- Approved

### Summary

- Verified Story 6.4 implementation against acceptance criteria and completed task checklist.
- Confirmed owner-scoped no-leak behavior for missing/cross-owner export IDs on `GET /exports/{exportId}`.
- Confirmed read-only polling semantics and download URL visibility policy (only present for `SUCCEEDED`).
- Confirmed OpenAPI contract assertions for `/api/v1/exports/{exportId}` response codes and schema refs.

### Severity Breakdown

- High: 0
- Medium: 0
- Low: 0
