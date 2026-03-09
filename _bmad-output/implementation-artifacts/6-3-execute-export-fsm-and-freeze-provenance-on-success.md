# Story 6.3: Execute Export FSM and Freeze Provenance on Success

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want export execution to follow deterministic lifecycle states,
so that retries and completion behavior are predictable.

## Acceptance Criteria

1. Given export lifecycle processing, when state transitions occur, then export FSM is `REQUESTED -> RUNNING -> SUCCEEDED|FAILED` and illegal transitions are rejected.
2. Given export reaches `SUCCEEDED`, when completion is persisted, then provenance is frozen and immutable and artifact linkage references frozen provenance and identity key.
3. Given duplicate execution trigger for same identity key, when processed, then execution is idempotent and duplicate artifacts are not created.

## Tasks / Subtasks

- [x] Implement export FSM lifecycle enforcement for execution transitions (AC: 1)
- [x] Add an export transition guard (domain-level) enforcing `REQUESTED -> RUNNING -> SUCCEEDED|FAILED` and rejecting illegal/self-terminal transitions.
- [x] Ensure all export status mutations flow through the guard; direct status assignment is forbidden outside validated transition helpers.
- [x] Return contract-safe conflict behavior for invalid transitions with no mutation side effects.
- [x] Implement success freeze semantics and linkage persistence (AC: 2)
- [x] On first successful completion, set `provenance_frozen_at` and prevent subsequent provenance mutation.
- [x] Keep frozen provenance exactly equal to request-time provenance snapshot (no recomputation or floating lookups at completion time).
- [x] Persist deterministic artifact linkage to job manifest/history (`artifact_manifest.exports`) without duplicate entries.
- [x] Ensure linkage references export identity (`export_id`, `identity_key`) tied to frozen provenance context.
- [x] Harden idempotent execution and replay behavior (AC: 3)
- [x] Ensure duplicate "start execution" or "complete success/failure" signals for the same export are replay-safe no-ops.
- [x] Ensure duplicate execution paths do not create duplicate artifacts, records, or inconsistent timestamps.
- [x] Preserve deterministic response/state for repeated triggers on identical export identity.
- [x] Add AC-mapped API/unit/OpenAPI coverage (AC: 1, 2, 3)
- [x] Add unit tests for valid/invalid export FSM transitions and terminal immutability behavior.
- [x] Add API/unit tests proving `SUCCEEDED` freeze semantics and immutable provenance on replay/duplicate completion attempts.
- [x] Add tests proving `artifact_manifest.exports` linkage is deterministic and de-duplicated.
- [x] Add regression tests for illegal transition rejection with no write-side effects.
- [x] Re-verify `/openapi.json` contract alignment for export schemas/status enums and no undocumented endpoint/status drift.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

## Dev Notes

### Developer Context Section

- Story 6.1 established deterministic export identity-key creation and create-request idempotency (`202` first, `200` replay).
- Story 6.2 established complete persisted provenance (`instruction_version_id`, `screenshot_set_hash`, anchor bindings, snapshot/model/prompt refs) and snapshot-scoped fallback refs.
- Story 6.3 adds execution lifecycle rigor and provenance freeze semantics without expanding public endpoint surface.
- Keep strict contract-first discipline: no spec changes in this story.

### Technical Requirements

- Primary scope:
- Export execution lifecycle for already-created exports seeded by `POST /jobs/{jobId}/exports`.
- Enforce export status model `REQUESTED -> RUNNING -> SUCCEEDED|FAILED`.
- Reject illegal transitions deterministically with no side effects.
- Success semantics:
- On transition to `SUCCEEDED`, set `provenance_frozen_at` (single-write behavior).
- Freeze and protect provenance from post-success mutation/drift.
- Persist artifact linkage to job history/manifest in a deterministic, de-duplicated way.
- Idempotency semantics:
- Duplicate execution triggers for same export identity must be no-op and must not create duplicate artifacts.
- Replays must return consistent export state and preserved provenance snapshot.
- Story boundaries:
- `GET /exports/{exportId}` response shaping/polling behavior is Story 6.4.
- Signed URL issuance policy is Story 6.5.
- Canonical export audit-event stream expansion is Story 6.6.

### Architecture Compliance

- `spec/` is read-only source of truth.
- Preserve thin route handlers and service/repository ownership for state mutations.
- If any job status mutation is required (for example `EXPORTING`/`DONE` lifecycle alignment), it must flow through `domain/job_fsm.ensure_transition(...)`.
- Export execution must be idempotent and replay-safe under duplicate trigger conditions.
- Preserve no-existence-leak behavior for owner-scoped access paths.
- Never persist or log raw prompt text/transcript content in export execution paths.

### Library & Framework Requirements

- FastAPI + Pydantic remain contract authority.
- Reuse current in-memory repository patterns (copy-on-read, deterministic sort/hash, replay maps).
- Follow existing domain-FSM pattern style (`app/domain/job_fsm.py`) when implementing export transition guardrails.
- No new dependencies expected.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/domain/export_fsm.py` (new export lifecycle transition guard)
- `apps/api/app/repositories/memory.py` (export execution transition helpers, freeze semantics, manifest linkage/idempotency)
- `apps/api/app/services/jobs.py` (service orchestration for export execution state progression)
- `apps/api/app/schemas/job.py` (schema-level alignment only if required by contract behavior)
- `apps/api/app/main.py` (OpenAPI shaping alignment only if needed)
- `apps/api/tests/test_jobs_ownership.py` (API regression coverage for execution/freeze/idempotency semantics)
- `apps/api/tests/test_auth_middleware.py` (OpenAPI assertions for export contract stability)
- `apps/api/tests/test_job_fsm.py` and/or dedicated export FSM unit test module (transition validation coverage)

### Testing Requirements

- Validate legal export FSM transitions (`REQUESTED -> RUNNING -> SUCCEEDED|FAILED`).
- Validate illegal transitions are rejected with no mutation/write-count drift.
- Validate `provenance_frozen_at` is set on success and remains immutable on duplicate completion attempts.
- Validate export provenance payload remains stable after success freeze (no drift on replay).
- Validate `artifact_manifest.exports` linkage records successful export deterministically without duplicates.
- Validate duplicate execution triggers for same export identity are replay-safe with no duplicate artifacts.
- Validate `/openapi.json` remains aligned with export schema/enum contract and no response-code drift.
- Final verification gate: `make lint`, `make test`, `make check` in `apps/api`.

### Previous Story Intelligence

- Story 6.2 already guarantees complete provenance persistence; Story 6.3 must freeze exactly that persisted payload, not recompute it.
- Story 6.2 added fallback reference derivation as snapshot-scoped IDs (`<instruction_snapshot_id>:model-profile`, `<instruction_snapshot_id>:prompt-template`); freeze semantics must preserve these as-is.
- Story 6.1 code-review guardrails must remain intact:
- Reject `idempotency_key: null` as contract-invalid payload.
- Reject ambiguous instruction selection for same owner+job+version.

### Git Intelligence Summary

- Recent commit history shows a minimal-diff, contract-first implementation pattern with explicit OpenAPI assertions and deterministic behavior tests.
- Existing implementation centralizes export logic in `jobs` service + in-memory repository; continue this pattern for consistency.
- Prefer additive, focused tests over broad refactors to preserve velocity and reviewability.

### Project Structure Notes

- No standalone architecture artifact is present in planning outputs; use OpenAPI + PRD + Epic decomposition + existing code patterns as implementation constraints.
- Keep Story 6.3 strictly scoped to export execution FSM and provenance freeze semantics.
- Defer status retrieval/download URL and expanded audit-event concerns to Stories 6.4-6.6.

### References

- `spec/api/openapi.yaml` (`ExportStatus`, `Export`, `ExportProvenance`, `/jobs/{jobId}/exports`, `/exports/{exportId}`)
- `spec/domain/job_fsm.md` (export-related job lifecycle interactions and terminal invariants)
- `_bmad-output/planning-artifacts/epics.md` (Epic 6, Story 6.3)
- `_bmad-output/planning-artifacts/prd.md` (FR-025, FR-028, FR-030, FR-039, FR-040, FR-044)
- `spec/acceptance/tasks_codex_v1.md` (Task 15 export determinism/freeze baseline)
- `spec/acceptance/v1_mvp.md` (Export acceptance surface and job completion expectation)
- `_bmad-output/project-context.md` (contract-first, FSM/idempotency, artifact discipline)
- `_bmad-output/implementation-artifacts/6-1-create-export-request-bound-to-exact-instruction-version.md`
- `_bmad-output/implementation-artifacts/6-2-persist-complete-export-provenance-and-snapshot-references.md`
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
- `spec/domain/job_fsm.md`
- `apps/api/app/domain/export_fsm.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/services/jobs.py`
- `apps/api/tests/test_job_fsm.py`
- `apps/api/tests/test_jobs_ownership.py`
- `spec/acceptance/tasks_codex_v1.md`
- `spec/acceptance/v1_mvp.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/6-2-persist-complete-export-provenance-and-snapshot-references.md`

### Completion Notes List

- 2026-03-04: Created Story 6.3 artifact from sprint backlog with AC-mapped tasks for export FSM execution, success freeze semantics, and idempotent duplicate-trigger handling.
- 2026-03-04: Captured contract constraints from OpenAPI plus export determinism requirements from PRD/acceptance artifacts.
- 2026-03-04: Incorporated prior-story guardrails from Stories 6.1 and 6.2 to prevent regressions in export identity/provenance behavior.
- 2026-03-04: Ultimate context engine analysis completed - comprehensive developer guide created.
- 2026-03-04: Implemented export lifecycle guardrails with new `export_fsm` (`REQUESTED -> RUNNING -> SUCCEEDED|FAILED`) and terminal immutability/error semantics.
- 2026-03-04: Added repository/service execution helpers for start/success/failure flows with replay-safe behavior, success-time provenance freeze (`provenance_frozen_at`), and deterministic manifest export linkage de-duplication.
- 2026-03-04: Added unit coverage for export FSM transitions and export execution replay/freeze/no-leak behavior.
- 2026-03-04: Verification passed in `apps/api` via `make lint`, `make test`, and `make check` (`189` tests).
- 2026-03-04: Addressed senior code-review findings by wiring export execution through callback lifecycle handling, aligning `EXPORTING -> EDITING` failure recovery, preserving replay-safe duplicate start behavior after terminal export states, and synchronizing story file traceability.
- 2026-03-04: Re-verified quality gates in `apps/api` via `make lint`, `make test`, and `make check` (`190` tests).

### File List

- `_bmad-output/implementation-artifacts/6-3-execute-export-fsm-and-freeze-provenance-on-success.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/domain/job_fsm.py`
- `apps/api/app/domain/export_fsm.py`
- `apps/api/app/main.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/schemas/job.py`
- `apps/api/app/services/jobs.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_internal_callback_transactions.py`
- `apps/api/tests/test_job_fsm.py`
- `apps/api/tests/test_jobs_ownership.py`

### Change Log

- 2026-03-04: Created Story 6.3 artifact and moved sprint status from `backlog` to `ready-for-dev`.
- 2026-03-04: Started implementation and moved sprint status from `ready-for-dev` to `in-progress`.
- 2026-03-04: Implemented export execution FSM/freeze/idempotency primitives and AC-mapped unit coverage.
- 2026-03-04: Ran `make lint`, `make test`, and `make check` in `apps/api` successfully; moved story to `review`.
- 2026-03-04: Senior code review reported HIGH/MEDIUM issues (identity linkage traceability, export failure lifecycle behavior, replay-safe terminal start handling, callback wiring, and file-list drift); story moved to `in-progress` for fixes.
- 2026-03-04: Applied all review fixes, reran `make lint`, `make test`, and `make check` in `apps/api` successfully (`190` tests), and moved story to `done`.

## Senior Developer Review (AI)

### Reviewer

- `Codex` (AI Senior Developer Reviewer)
- Date: 2026-03-04

### Outcome

- Approved

### Summary

- Re-reviewed Story 6.3 after automatic fix pass and verified all previously raised HIGH/MEDIUM findings are resolved in code and tests.
- Export lifecycle execution is now callback-wired and deterministic; failure path restores editability, and duplicate start signals after terminal export states are replay-safe no-ops.
- Story traceability now reflects the full source/test working-set touched by this story cycle.

### Severity Breakdown

- High: 0
- Medium: 0
- Low: 0

### Resolved Items

- [x] [HIGH] Export linkage now retains `identity_key` alongside `export_id` in deterministic manifest-linkage history (`export_linkages_by_job`) while preserving contract-safe `artifact_manifest.exports` shape.
- [x] [HIGH] Export failure lifecycle now transitions the job back to `EDITING` via FSM-validated transition (`EXPORTING -> EDITING`).
- [x] [HIGH] Duplicate start-execution signals after terminal export states (`SUCCEEDED`/`FAILED`) are replay-safe no-ops.
- [x] [MEDIUM] Export execution lifecycle is now wired into internal callback processing using callback `artifact_updates.export_id` mapping.
- [x] [MEDIUM] Story File List has been synchronized with the complete current source/test change set.
