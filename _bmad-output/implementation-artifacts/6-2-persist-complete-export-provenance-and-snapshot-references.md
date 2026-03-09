# Story 6.2: Persist Complete Export Provenance and Snapshot References

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a compliance stakeholder,
I want each export to carry complete provenance,
so that output can be reproduced and audited.

## Acceptance Criteria

1. Given export request is accepted, when provenance is persisted, then provenance includes `instruction_version_id`, `screenshot_set_hash`, active anchor set, `active_asset_id` per anchor, and `rendered_asset_id` where annotated.
2. Given instruction and screenshot content for export, when source references are resolved, then export binds to stored instruction snapshot and immutable model and prompt references by IDs only, and raw prompt text is not stored in export provenance.

## Tasks / Subtasks

- [x] Complete export provenance persistence model for contract-required fields (AC: 1, 2)
- [x] Ensure persisted `Export.provenance` always includes `instruction_version_id`, `screenshot_set_hash`, and full anchor binding list in deterministic ordering.
- [x] Ensure each persisted anchor entry includes `anchor_id`, `active_asset_id`, and `rendered_asset_id` when active asset kind is annotated.
- [x] Preserve deterministic screenshot set hashing from canonicalized active anchor bindings; do not use floating/latest lookups outside the selected export scope.
- [x] Bind export to instruction snapshot and immutable model/prompt references by IDs (AC: 2)
- [x] Persist `instruction_snapshot_id` derived from the selected instruction version used for export identity generation.
- [x] Persist `model_profile_id`, `prompt_template_id`, and `prompt_params_ref` from the selected instruction version context used for the request.
- [x] Ensure provenance does not persist raw prompt text or transcript content.
- [x] Harden provenance correctness and replay behavior (AC: 1, 2)
- [x] Keep replay behavior idempotent on identity key with no duplicate export records or provenance drift.
- [x] Ensure ambiguous/missing instruction-version context remains rejected with contract-safe `400 EXPORT_REQUEST_INVALID` and no mutation.
- [x] Add AC-mapped API/unit/OpenAPI coverage (AC: 1, 2)
- [x] Add API tests asserting provenance payload completeness and exact anchor binding behavior for mixed active asset kinds (`EXTRACTED`, `UPLOADED`, `ANNOTATED`).
- [x] Add API tests asserting snapshot and model/prompt ID references are persisted and returned in export payload without raw prompt text fields.
- [x] Add regression tests for deterministic provenance anchor ordering and replay stability of persisted provenance.
- [x] Extend OpenAPI assertions for provenance schema refs/required properties used by this story scope.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

## Dev Notes

### Developer Context Section

- Story 6.1 already shipped `POST /jobs/{jobId}/exports` with deterministic identity-key creation, idempotent `202/200` replay semantics, and owner-scoped no-leak behavior.
- Story 6.2 deepens provenance persistence quality for reproducibility/auditability while staying inside the existing export-create endpoint surface.
- Keep contract-first discipline strict: no new endpoints/status codes/schema fields beyond `spec/api/openapi.yaml`.

### Technical Requirements

- Endpoint in scope:
- `POST /jobs/{jobId}/exports` (existing; deepen provenance persistence semantics)
- Contract requirements from OpenAPI:
- `ExportProvenance.required` must include `instruction_version_id`, `screenshot_set_hash`, `anchors`, `instruction_snapshot_id`, `model_profile_id`, `prompt_template_id`.
- `ExportAnchorBinding.required` must include `anchor_id` and `active_asset_id`; `rendered_asset_id` is nullable.
- `CreateExportRequest` identity remains deterministic by `instruction_version_id + format + screenshot_set_hash`.
- Provenance constraints:
- Persist export provenance from selected instruction-version context only.
- Persist immutable model/prompt references by ID fields only (`model_profile_id`, `prompt_template_id`, `prompt_params_ref`).
- Do not persist raw prompt text in export provenance.
- Story boundaries:
- Export FSM progression, provenance freeze semantics, and export status/download endpoints belong to Stories 6.3-6.5.

### Architecture Compliance

- `spec/` is read-only source of truth.
- Keep route handlers thin; provenance assembly and persistence logic belongs in service/repository layers.
- Maintain no-existence-leak behavior (`404`) for unknown/cross-owner jobs.
- Preserve idempotent replay safety and deterministic canonicalization.
- Respect artifact discipline by keeping provenance references explicit and reproducible; do not introduce implicit floating references.

### Library & Framework Requirements

- FastAPI + Pydantic remain request/response contract authority.
- Reuse existing in-memory repository patterns for deterministic keying, copy-on-read records, and owner scoping.
- Reuse OpenAPI shaping and response-code assertions in `app/main.py` and `test_auth_middleware.py`.
- No new dependencies expected.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/schemas/job.py` (export provenance model semantics/validation as needed)
- `apps/api/app/services/jobs.py` (provenance construction, instruction snapshot/model-prompt ref binding)
- `apps/api/app/repositories/memory.py` (provenance persistence helpers and deterministic anchor binding extraction)
- `apps/api/app/main.py` (OpenAPI shaping alignment, if schema output adjustments are required)
- `apps/api/tests/test_jobs_ownership.py` (API/unit coverage for provenance completeness and deterministic replay)
- `apps/api/tests/test_auth_middleware.py` (OpenAPI contract assertions)

### Testing Requirements

- Validate accepted export request returns provenance with:
- `instruction_version_id`
- `screenshot_set_hash`
- `anchors` containing complete active anchor set with per-anchor `active_asset_id` and `rendered_asset_id` when annotated
- `instruction_snapshot_id`
- `model_profile_id`, `prompt_template_id`, optional `prompt_params_ref`
- Validate no raw prompt text fields are introduced in provenance payload/persistence.
- Validate provenance remains deterministic and stable on idempotent replay for the same identity key.
- Validate ambiguous or invalid instruction-version context still yields `400 EXPORT_REQUEST_INVALID` with no export mutation.
- Validate `/openapi.json` remains aligned for export provenance schema refs/required fields.
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Story 6.1 introduced export create models/route/service/repository paths and deterministic identity-key replay behavior.
- Code-review remediation from Story 6.1 added two critical guardrails that must be preserved:
- Reject `idempotency_key: null` as contract-invalid payload.
- Reject ambiguous instruction selection when multiple instructions share the same owner+job+version.
- Story 6.2 should build on those guardrails, not bypass them.

### Git Intelligence Summary

- Recent commit history indicates a minimal-diff, contract-first implementation style with explicit OpenAPI assertions and no-leak ownership enforcement.
- Existing tests are comprehensive and extended in-place; keep adding focused regressions rather than refactoring broad test structure.
- Export-related implementation currently lives in `jobs` service/repository/schema surfaces; continue that pattern for consistency.

### Project Structure Notes

- No standalone architecture artifact is present in planning outputs for this project; use OpenAPI + PRD + Epic decomposition + existing code patterns as primary constraints.
- Keep Story 6.2 scoped to provenance completeness and immutable reference binding only.
- Do not implement Story 6.3+ responsibilities here (FSM execution/freeze/status/download/audit event progression).

### References

- `spec/api/openapi.yaml` (`ExportProvenance`, `ExportAnchorBinding`, `Export`, `/jobs/{jobId}/exports`)
- `_bmad-output/planning-artifacts/epics.md` (Epic 6, Story 6.2)
- `_bmad-output/planning-artifacts/prd.md` (FR-039, FR-040, FR-044)
- `spec/acceptance/tasks_codex_v1.md` (Task 15 export determinism baseline)
- `spec/acceptance/v1_mvp.md` (Export acceptance surface and constraints)
- `_bmad-output/project-context.md` (contract-first, idempotency, artifact discipline, security/logging constraints)
- `_bmad-output/implementation-artifacts/6-1-create-export-request-bound-to-exact-instruction-version.md`
- `apps/api/app/schemas/job.py`
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
- `spec/acceptance/v1_mvp.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/6-1-create-export-request-bound-to-exact-instruction-version.md`

### Completion Notes List

- 2026-03-04: Created Story 6.2 artifact from sprint backlog with AC-mapped tasks focused on complete export provenance persistence and immutable snapshot/reference binding.
- 2026-03-04: Captured contract requirements and constraints from OpenAPI, PRD (`FR-039`, `FR-040`, `FR-044`), and Epic 6 scope boundaries.
- 2026-03-04: Included previous-story intelligence from Story 6.1 (idempotency and ambiguity guardrails) to prevent regressions in provenance persistence work.
- 2026-03-04: Marked story ready for development with explicit verification gates (`make lint`, `make test`, `make check`).
- 2026-03-04: Added export provenance tests covering mixed active asset kinds (`EXTRACTED`, `UPLOADED`, `ANNOTATED`), deterministic anchor ordering, replay stability, and raw prompt/transcript non-persistence checks.
- 2026-03-04: Updated export provenance fallback behavior to derive snapshot-scoped reference IDs (`<instruction_snapshot_id>:model-profile`, `<instruction_snapshot_id>:prompt-template`) when instruction references are absent.
- 2026-03-04: Extended OpenAPI assertions for `ExportProvenance` property contract shape and re-verified full suite.
- 2026-03-04: Verification passed in `apps/api` via `make lint`, `make test`, and `make check` (`182` tests).
- 2026-03-04: Completed code review with no HIGH/MEDIUM findings; verified AC/task claims against implementation and moved story to `done`.

### File List

- `_bmad-output/implementation-artifacts/6-2-persist-complete-export-provenance-and-snapshot-references.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/services/jobs.py`
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_auth_middleware.py`

### Change Log

- 2026-03-04: Created Story 6.2 artifact and moved sprint status from `backlog` to `ready-for-dev`.
- 2026-03-04: Implemented Story 6.2 export provenance completeness and snapshot-scoped reference ID persistence; added AC-mapped API/OpenAPI coverage and verification; moved story status to `review`.
- 2026-03-04: Completed code-review validation, approved implementation, and moved story/sprint status to `done`.

## Senior Developer Review (AI)

### Reviewer

- `Codex` (AI Senior Developer Reviewer)
- Date: 2026-03-04

### Outcome

- Approved

### Summary

- Verified Story 6.2 acceptance criteria and all checked tasks against implementation in `jobs` service/repository/schema/openapi test surfaces.
- Confirmed provenance completeness for mixed active asset kinds, deterministic anchor ordering/hash identity, replay stability, and snapshot/model/prompt ID-only persistence.
- Confirmed no raw prompt/transcript fields are persisted in export provenance payloads.
- Re-ran quality gates in `apps/api`:
  - `HOWERA_CALLBACK_SECRET=test-secret make lint`
  - `HOWERA_CALLBACK_SECRET=test-secret make test`
  - `HOWERA_CALLBACK_SECRET=test-secret make check`

### Severity Breakdown

- High: 0
- Medium: 0
- Low: 0
