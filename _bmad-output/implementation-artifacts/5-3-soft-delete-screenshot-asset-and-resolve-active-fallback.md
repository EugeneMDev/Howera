# Story 5.3: Soft-Delete Screenshot Asset and Resolve Active Fallback

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to soft-delete a screenshot asset and unlink it from active anchor use,
so that obsolete visuals are removed without mutating immutable raw artifacts.

## Acceptance Criteria

1. Given soft-delete request for owned asset linked to anchor, when deletion is applied, then asset is marked soft-deleted and deleted assets are excluded from active selection by default.
2. Given deleted asset equals anchor `active_asset_id`, when fallback policy executes, then anchor `active_asset_id` resolves to previous valid version if available, and otherwise resolves to `null` (unbound state).
3. Given deleted assets exist, when history or audit query is requested, then deleted versions remain queryable for history and are clearly marked non-active.

## Tasks / Subtasks

- [x] Implement soft-delete contract and route/service boundary (AC: 1, 2, 3)
- [x] Add `SoftDeleteScreenshotAssetResponse` schema aligned to OpenAPI (`anchor_id`, `deleted_asset_id`, `active_asset_id`).
- [x] Implement `DELETE /anchors/{anchorId}/assets/{assetId}` as a thin route handler with service-owned ownership checks.
- [x] Keep response set contract-safe (`200`, `404`) with no write-side effects on reject paths.
- [x] Implement owner/no-leak behavior for missing or cross-owner anchor/asset references.
- [x] Implement screenshot asset soft-delete persistence and deterministic fallback (AC: 1, 2)
- [x] Extend screenshot asset persistence model to include soft-delete state (`is_deleted`) with deterministic updates.
- [x] Add repository delete operation that validates anchor-asset linkage and marks target asset deleted without mutating immutable raw artifacts.
- [x] If deleted asset is current active, compute fallback by version-chain traversal (`previous_asset_id`) to the latest non-deleted candidate.
- [x] If no non-deleted fallback exists, set anchor `active_asset_id` to `null`.
- [x] Preserve idempotent behavior for repeated delete of same owned asset (return current post-delete state without duplicate side effects).
- [x] Implement history visibility semantics for deleted assets (AC: 1, 3)
- [x] Ensure deleted assets are excluded from active selection logic by default.
- [x] Ensure deleted assets remain queryable for owner-scoped history/audit retrieval and are surfaced as non-active (`is_deleted=true`).
- [x] Add AC-mapped API/unit/OpenAPI coverage (AC: 1, 2, 3)
- [x] Add API tests for successful delete response shape and owner/no-leak `404` cases.
- [x] Add API tests covering active fallback resolution: previous valid version selected, otherwise `null`.
- [x] Add API tests for deleting non-active assets (active pointer unchanged) and repeated delete idempotency.
- [x] Add unit tests for fallback traversal across mixed deleted/non-deleted version chains.
- [x] Add unit tests ensuring deleted assets remain history-queryable and marked non-active.
- [x] Re-verify `/openapi.json` includes `/anchors/{anchorId}/assets/{assetId}` with expected response codes/schema refs.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

## Dev Notes

### Developer Context Section

- Story 5.2 established replace-versioning behavior (`previous_asset_id` linkage + `active_asset_id` updates) and owner/no-leak boundaries for anchor operations.
- Story 5.3 extends the same asset-chain model with soft-delete semantics and deterministic active fallback.
- Contract-first discipline is mandatory: endpoint, response payload, and status codes must exactly match `spec/api/openapi.yaml`.

### Technical Requirements

- Endpoint in scope:
- `DELETE /anchors/{anchorId}/assets/{assetId}`
- Contract behavior from OpenAPI:
- `200`: `SoftDeleteScreenshotAssetResponse` (`anchor_id`, `deleted_asset_id`, `active_asset_id`)
- `404`: no-leak for unauthorized/missing anchor or asset.
- Model requirements from OpenAPI:
- `ScreenshotAsset` includes required `is_deleted` field.
- Deleted assets must be non-active and retained for history queryability.
- Fallback policy:
- If deleting active asset, resolve to previous non-deleted version via version chain.
- If no valid fallback exists, anchor becomes unbound (`active_asset_id = null`).

### Architecture Compliance

- `spec/` is read-only source of truth.
- Keep route handlers thin; enforce ownership, linkage validation, delete semantics, and fallback in service/repository layers.
- Preserve no-existence-leak behavior (`404`) for missing and unauthorized resources.
- Preserve artifact discipline:
- no mutable overwrite/deletion of immutable raw artifacts.
- screenshot assets remain version-linked records; delete is a soft state transition only.
- Maintain secure logging boundaries (no secrets/raw transcript leakage).

### Library & Framework Requirements

- FastAPI + Pydantic remain API contract authority.
- Reuse existing screenshot persistence/service patterns from Stories 5.1/5.2.
- Reuse existing deterministic write-counter and no-side-effect assertion patterns in tests.
- No new dependencies expected.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/schemas/job.py` (add `SoftDeleteScreenshotAssetResponse`; extend screenshot asset schema fields as needed for contract alignment)
- `apps/api/app/routes/jobs.py` (add `DELETE /anchors/{anchorId}/assets/{assetId}`)
- `apps/api/app/services/jobs.py` (add owner-scoped delete operation and fallback policy boundary)
- `apps/api/app/repositories/memory.py` (persist `is_deleted`, anchor/asset linkage validation, deterministic fallback traversal, idempotent delete replay)
- `apps/api/app/main.py` (OpenAPI response-code allowlist and screenshot schema shaping for delete path/refs)
- `apps/api/tests/test_jobs_ownership.py` (API/unit tests for soft-delete behavior, fallback rules, no-leak enforcement)
- `apps/api/tests/test_auth_middleware.py` (OpenAPI path/schema assertions for delete endpoint)

### Testing Requirements

- Validate successful soft-delete returns `200` with `anchor_id`, `deleted_asset_id`, and resolved `active_asset_id`.
- Validate unknown/non-owned anchor or asset returns no-leak `404`.
- Validate deleting active asset selects previous non-deleted version when present.
- Validate deleting active asset with no valid fallback sets `active_asset_id` to `null`.
- Validate deleting non-active asset does not change active pointer.
- Validate repeated delete for same asset is idempotent and side-effect-safe.
- Validate deleted assets are preserved for history retrieval and clearly marked non-active (`is_deleted=true`).
- Validate `/openapi.json` includes `/anchors/{anchorId}/assets/{assetId}` with `200/404` and correct schema refs.
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Story 5.2 delivered:
- owner-scoped anchor lookup and instruction-version context validation.
- version-chain persistence (`version`, `previous_asset_id`, `active_asset_id`) used by replace completion.
- canonical/idempotency replay semantics with write-count side-effect guardrails in tests.
- Carry forward strict no-leak responses and deterministic persistence updates to avoid regressions in screenshot lifecycle behavior.

### Git Intelligence Summary

- Recent commits indicate disciplined, story-scoped backend delivery with contract-first validation (`4-3-update-instruction-markdown-with-versioning-and-concurrency-control`, prior FSM and workflow stories).
- Existing implementation patterns in this branch favor:
- thin routes with service-owned decisions
- deterministic repository updates
- explicit ownership/no-leak checks
- OpenAPI shaping + assertion tests in `test_auth_middleware.py`
- Follow the same minimal-diff pattern for Story 5.3.

### Project Structure Notes

- No standalone architecture artifact exists under `_bmad-output/planning-artifacts/`; use `epics.md`, `prd.md`, OpenAPI, and current screenshot lifecycle implementation as primary guardrails.
- Keep Story 5.3 scope focused on soft-delete + fallback semantics; upload/attach/annotation and anchor addressing persistence are covered by later Epic 5 stories.

### References

- `spec/api/openapi.yaml` (`/anchors/{anchorId}/assets/{assetId}`, `SoftDeleteScreenshotAssetResponse`, `ScreenshotAsset`, `ScreenshotAnchor`)
- `_bmad-output/planning-artifacts/epics.md` (Epic 5, Story 5.3)
- `_bmad-output/planning-artifacts/prd.md` (FR-034; screenshot lifecycle constraints)
- `spec/acceptance/tasks_codex_v1.md` (Task 13 lifecycle expectations, deterministic active fallback)
- `_bmad-output/project-context.md` (contract-first API, idempotent processing, artifact discipline, no-leak policy)
- `_bmad-output/implementation-artifacts/5-2-replace-existing-screenshot-asset-for-anchor-with-versioning.md`
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
- `_bmad-output/implementation-artifacts/5-2-replace-existing-screenshot-asset-for-anchor-with-versioning.md`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/schemas/job.py`
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_auth_middleware.py`

### Completion Notes List

- 2026-03-01: Created Story 5.3 artifact with AC-mapped tasks, soft-delete/fallback constraints, and contract-safe implementation guardrails.
- 2026-03-01: Captured deterministic fallback requirements for active-asset deletion using version-chain linkage (`previous_asset_id`).
- 2026-03-01: Captured history visibility expectations for deleted assets (`is_deleted` non-active state with owner-scoped queryability).
- 2026-03-01: Ultimate context engine analysis completed - comprehensive developer guide created.
- 2026-03-01: Implemented `DELETE /anchors/{anchorId}/assets/{assetId}` with owner/no-leak safeguards and contract-safe `200/404` behavior.
- 2026-03-01: Added soft-delete persistence (`is_deleted`) and deterministic active fallback traversal across `previous_asset_id` version chains.
- 2026-03-01: Added API and unit coverage for fallback resolution, idempotent repeat delete, no-leak `404`, and history-queryable deleted assets.
- 2026-03-01: Verified with `make lint`, `make test`, and `make check` in `apps/api` (all passing).

### File List

- `_bmad-output/implementation-artifacts/5-3-soft-delete-screenshot-asset-and-resolve-active-fallback.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/schemas/job.py`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_jobs_ownership.py`

### Change Log

- 2026-03-01: Created Story 5.3 artifact and moved sprint status from `backlog` to `ready-for-dev`.
- 2026-03-01: Implemented soft-delete screenshot asset API/repository/service flow with deterministic active fallback and idempotent repeat-delete behavior.
- 2026-03-01: Added OpenAPI contract shaping and assertions for `/anchors/{anchorId}/assets/{assetId}` (`200/404` with expected schema refs).
- 2026-03-01: Added API and unit tests for no-leak ownership, fallback traversal across deleted versions, and history-queryable deleted assets.
- 2026-03-01: Ran `make lint`, `make test`, and `make check` in `apps/api`; moved story to `review`.
- 2026-03-01: Senior Developer Review completed with approval; no remaining HIGH/MEDIUM findings; moved story to `done`.

## Senior Developer Review (AI)

### Outcome

- Approved.
- No HIGH or MEDIUM findings.

### Findings

- No actionable defects were identified in Story 5.3 implementation against current acceptance criteria and OpenAPI contract checks.

### Residual Risks / Testing Gaps

- Deleted-asset history visibility is currently verified through owner-scoped repository retrieval and API behavior; dedicated anchor/history query endpoints are planned in later Epic 5 stories and will need explicit integration coverage when introduced.

### Verification Evidence

- `make check` in `apps/api` passed on 2026-03-01 (`lint` + `test`, 153 tests total).
