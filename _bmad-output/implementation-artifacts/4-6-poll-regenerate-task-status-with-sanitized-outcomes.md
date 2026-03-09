# Story 4.6: Poll Regenerate Task Status with Sanitized Outcomes

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to poll regenerate task status,
so that I can detect completion or failure and fetch safe outcome metadata.

## Acceptance Criteria

1. Given owned regenerate task ID, when task is polled, then API returns contract-defined state and progress metadata.
2. Given task state is `SUCCEEDED`, when status response is returned, then response includes reference to the new instruction version (`instruction_id`, `version`, or contract equivalent).
3. Given task state is `FAILED`, when status response is returned, then response includes sanitized failure fields only (`failure_code`, safe message, `failed_stage` if applicable) and excludes secrets, raw transcript, and prompt content.
4. Given task ID is unknown or unauthorized, when status is polled, then no-existence-leak policy is applied (`404`).

## Tasks / Subtasks

- [x] Implement regenerate-task read endpoint and owner-scoped service boundary (AC: 1, 2, 3, 4)
- [x] Implement `GET /tasks/{taskId}` route with thin handler and service-bound ownership/read logic.
- [x] Return contract response model `RegenerateTask` on success and no-leak `404 RESOURCE_NOT_FOUND` for unknown/non-owned tasks.
- [x] Keep response set contract-safe (`200`, `404`) with no undocumented status-code drift.
- [x] Implement task retrieval behavior for all task states (AC: 1, 2, 3)
- [x] Return `status`, `progress_pct`, `requested_at`, `updated_at`, and provenance metadata for owned tasks.
- [x] For `SUCCEEDED` state, ensure response includes `instruction_id` and `instruction_version` from persisted task linkage.
- [x] For `FAILED` state, ensure response exposes only sanitized failure fields (`failure_code`, safe `failure_message`, optional `failed_stage`).
- [x] Preserve replay metadata semantics (`replayed` field) per contract for task payload consistency.
- [x] Preserve sanitization and no-leak guarantees in task polling paths (AC: 3, 4)
- [x] Ensure no transcript/prompt/secret values are surfaced in `failure_message`, provenance echoes, or logs.
- [x] Ensure task polling does not mutate project/job/instruction/task state (read-only path).
- [x] Ensure unauthorized/nonexistent task requests remain indistinguishable (`404` no-leak behavior).
- [x] Add AC-mapped tests + regression coverage (AC: 1, 2, 3, 4)
- [x] Add API tests for polling owned task in `PENDING`/`RUNNING` with contract-compliant metadata fields.
- [x] Add API tests for `SUCCEEDED` task response containing `instruction_version` linkage.
- [x] Add API tests for `FAILED` task response containing only sanitized failure fields.
- [x] Add API tests for unknown/non-owned task no-leak `404` and no-side-effect assertions.
- [x] Add service/repository unit tests for owner-scoped task lookup and read-only guarantees.
- [x] Re-verify `/openapi.json` includes `/tasks/{taskId}` `GET` schema and response set alignment.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

## Dev Notes

### Developer Context Section

- Epic 4 introduces regenerate flows across request, processing, and quality validation. Story 4.5 implemented regenerate request intake (`POST /instructions/{instructionId}/regenerate`) with idempotency/provenance/task persistence.
- Story 4.6 is the polling counterpart for task visibility, and must expose task outcomes safely without leaking sensitive content.
- Story 4.6 must preserve no-leak ownership semantics and contract-safe response shaping established in Stories 4.2–4.5.

### Technical Requirements

- Endpoint in scope: `GET /tasks/{taskId}`.
- Contract behavior from OpenAPI:
  - `200`: `RegenerateTask` payload.
  - `404`: `NoLeakNotFoundError` for missing/non-owned task.
- Response semantics:
  - task states: `PENDING | RUNNING | SUCCEEDED | FAILED`
  - include progress metadata (`progress_pct`) and timing metadata (`requested_at`, `updated_at`)
  - `SUCCEEDED` must include `instruction_version` reference
  - `FAILED` must expose sanitized failure fields only
- Ownership/no-leak:
  - task polling must be owner-scoped
  - unknown/non-owned responses must be identical `404 RESOURCE_NOT_FOUND`
- Read-only behavior:
  - polling endpoint must not mutate task/job/instruction/project state.

### Architecture Compliance

- `spec/` is read-only source of truth.
- Keep business logic out of routes; implement ownership scoping and task-read semantics in service/repository boundaries.
- Preserve no-existence-leak behavior for editor-facing resources.
- Preserve secure logging boundaries: no transcript/prompt content/secrets in logs or task failure messages.
- Reuse existing regenerate task persistence structures from Story 4.5 to avoid duplicated state models.

### Library & Framework Requirements

- FastAPI + Pydantic contracts remain authoritative.
- Reuse existing schemas: `RegenerateTask`, `NoLeakNotFoundError`.
- Reuse established error handling (`ApiError` mapping to contract payloads).
- No new dependencies expected.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/routes/instructions.py` (add `GET /tasks/{taskId}` handler)
- `apps/api/app/services/instructions.py` (add task-polling service boundary with owner scoping)
- `apps/api/app/repositories/memory.py` (owner-scoped regenerate-task retrieval helper usage, if additional helpers required)
- `apps/api/app/main.py` (OpenAPI response-set shaping/contract enforcement for `/tasks/{taskId}` as needed)
- `apps/api/tests/test_instructions_ownership.py` (task polling API/service regression tests)
- `apps/api/tests/test_auth_middleware.py` (OpenAPI contract assertions)

### Testing Requirements

- Validate owned-task polling returns `200` with contract-compliant metadata.
- Validate `SUCCEEDED` task payload includes instruction-version linkage fields.
- Validate `FAILED` task payload includes sanitized failure fields only.
- Validate non-owned/missing task returns no-leak `404` with no side effects.
- Validate polling path is read-only (no write-counter increments for reject/success reads).
- Validate `/openapi.json` includes `/tasks/{taskId}` `GET` with `200/404` and correct schema refs.
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Story 4.5 implemented regenerate task persistence, idempotency signatures, provenance, and success/failure task updates.
- Story 4.5 review fixes hardened replay semantics after instruction version advancement and aligned `RegenerateSelection` OpenAPI `oneOf` contract.
- Story 4.4 centralized validation-on-write; Story 4.6 should not bypass or mutate instruction data when polling.
- Prior Epic 4 reviews repeatedly identified OpenAPI/runtime contract drift risks; keep explicit schema/response assertions for `/tasks/{taskId}`.

### Git Intelligence Summary

- Existing backend patterns favor:
- thin routes with service-bound business logic
- deterministic in-memory repository behavior and owner-scoped lookup helpers
- explicit no-side-effect assertions in tests for reject paths
- contract-shaping assertions in `test_auth_middleware.py`
- Story 4.6 should extend these patterns with minimal diff and no unrelated refactor.

### Project Structure Notes

- No standalone architecture artifact is present in `_bmad-output/planning-artifacts/`; use `epics.md`, `prd.md`, OpenAPI, and recent Story 4.x artifacts as implementation guardrails.
- Keep scope focused on polling `GET /tasks/{taskId}` only; do not expand into screenshot/export task polling in this story.

### References

- `spec/api/openapi.yaml` (`RegenerateTask`, `/tasks/{taskId}`, `NoLeakNotFoundError`)
- `_bmad-output/planning-artifacts/epics.md` (Epic 4, Story 4.6)
- `_bmad-output/planning-artifacts/prd.md` (FR-021 contract-first constraints)
- `spec/acceptance/tasks_codex_v1.md` (Task 10 task-polling acceptance intent)
- `_bmad-output/project-context.md` (async idempotency, security boundaries, no-leak behavior)
- `_bmad-output/implementation-artifacts/4-4-structural-validation-on-create-and-update-with-persisted-result.md`
- `_bmad-output/implementation-artifacts/4-5-request-targeted-regeneration-with-idempotency-and-provenance.md`
- `apps/api/app/routes/instructions.py`
- `apps/api/app/services/instructions.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_instructions_ownership.py`
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
- `_bmad-output/implementation-artifacts/4-4-structural-validation-on-create-and-update-with-persisted-result.md`
- `_bmad-output/implementation-artifacts/4-5-request-targeted-regeneration-with-idempotency-and-provenance.md`
- `apps/api/app/routes/instructions.py`
- `apps/api/app/services/instructions.py`
- `apps/api/app/repositories/memory.py`

### Completion Notes List

- 2026-03-01: Created Story 4.6 artifact with task-polling requirements, AC-mapped tasks, and implementation guardrails.
- 2026-03-01: Captured contract-safe polling semantics for `/tasks/{taskId}` including no-leak ownership and sanitized failure outcomes.
- 2026-03-01: Incorporated continuity guardrails from Story 4.5 task persistence and Story 4.4 validation boundaries.
- 2026-03-01: Ultimate context engine analysis completed - comprehensive developer guide created.
- 2026-03-01: Implemented owner-scoped task polling via `GET /tasks/{taskId}` with thin route + service boundary and no-leak `404` semantics.
- 2026-03-01: Added OpenAPI contract shaping/coverage for `/tasks/{taskId}` and API/unit regression tests across `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, and unauthorized/missing no-leak cases.
- 2026-03-01: Verified quality gates in `apps/api` with `make lint`, `make test`, and `make check` (all passing).

### File List

- `_bmad-output/implementation-artifacts/4-6-poll-regenerate-task-status-with-sanitized-outcomes.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/routes/instructions.py`
- `apps/api/app/services/instructions.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_instructions_ownership.py`
- `apps/api/tests/test_auth_middleware.py`

### Change Log

- 2026-03-01: Created Story 4.6 artifact and moved sprint status from `backlog` to `ready-for-dev`.
- 2026-03-01: Started development and moved sprint status from `ready-for-dev` to `in-progress`.
- 2026-03-01: Implemented task polling route/service/OpenAPI shaping and AC-mapped API + unit coverage for sanitized outcomes, owner scoping, and no-side-effect reads.
- 2026-03-01: Ran `make lint`, `make test`, and `make check` in `apps/api` successfully; moved story to `review`.
- 2026-03-01: Completed code-review with no HIGH/MEDIUM findings; moved story and sprint status to `done`.

## Senior Developer Review (AI)

### Reviewer

- `Codex` (AI Senior Developer Reviewer)
- Date: 2026-03-01

### Outcome

- Approved

### Summary

- Verified Story 4.6 implementation against all acceptance criteria and checked tasks marked complete.
- Confirmed owner-scoped no-leak polling behavior, sanitized failed outcomes, and contract-aligned OpenAPI shape for `GET /tasks/{taskId}`.
- Confirmed API and unit regression coverage exists for `PENDING`/`RUNNING`/`SUCCEEDED`/`FAILED` and non-owner/missing `404` behavior.

### Severity Breakdown

- High: 0
- Medium: 0
- Low: 0
