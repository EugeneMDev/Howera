# Story 5.4: Upload Custom Image via Signed URL and Confirm Attach

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to upload a custom image and attach it to an anchor,
so that I can use manual visuals when extraction is insufficient.

## Acceptance Criteria

1. Given editor requests custom image upload, when API issues upload authorization, then signed upload URL is returned with contract-defined expiry and constraints.
2. Given uploaded file confirm step is called, when validation runs, then allowed MIME types are enforced (`image/png`, `image/jpeg`, `image/webp`), size limits are enforced, and checksum and dimensions are captured and persisted.
3. Given file is SVG, when confirmation is attempted, then upload is rejected unless contract-approved sanitizer flow exists, and default behavior disallows unsanitized SVG.
4. Given attach-to-anchor is requested, when confirmation succeeds, then asset versioning and anchor `active_asset_id` update are applied transactionally.

## Tasks / Subtasks

- [x] Implement custom upload ticket contract and route/service boundary (AC: 1, 2, 3)
- [x] Add request/response schemas aligned to OpenAPI: `CreateCustomUploadRequest`, `CustomUploadTicket`, `ConfirmCustomUploadRequest`, `ConfirmCustomUploadResponse`, `AttachUploadedAssetRequest`.
- [x] Implement `POST /jobs/{jobId}/screenshots/uploads` as a thin route handler with service-owned ownership/no-leak behavior.
- [x] Return `201` with `upload_id`, signed `upload_url`, `expires_at`, `max_size_bytes`, and `allowed_mime_types`.
- [x] Keep response sets contract-safe for upload endpoints (`201/404` for ticket, `200/404` for confirm, `200/404` for attach).
- [x] Implement owner/no-leak behavior for missing/cross-owner job, upload, and anchor references.
- [x] Implement custom upload confirmation validation and persistence (AC: 2, 3)
- [x] Enforce MIME allowlist (`image/png`, `image/jpeg`, `image/webp`) and reject unsupported content, including unsanitized SVG by default.
- [x] Enforce size and basic integrity validation (`size_bytes`, `checksum_sha256`, `width`, `height`) before persistence.
- [x] Persist confirmed uploaded asset metadata needed by contract and lifecycle (`asset` in confirm response; kind/version/linkage fields as required by current model).
- [x] Ensure validation failures do not create partial upload/asset state.
- [x] Implement attach-upload flow with transactional versioning semantics (AC: 4)
- [x] Implement `POST /anchors/{anchorId}/attach-upload` to bind confirmed upload to owned anchor/instruction context.
- [x] Apply deterministic version-chain update on attach: new uploaded asset version linked via `previous_asset_id`, anchor `active_asset_id` switched atomically.
- [x] Implement idempotent behavior for `idempotency_key` on attach where supported by story policy.
- [x] Add AC-mapped API/unit/OpenAPI coverage (AC: 1, 2, 3, 4)
- [x] Add API tests for ticket creation success (`201`) and no-leak `404` behavior.
- [x] Add API tests for confirm success (`200`) with persisted asset metadata and no-leak `404` behavior.
- [x] Add API tests for MIME/size validation failures, including explicit SVG rejection default path.
- [x] Add API tests for attach success (`200`) with anchor active pointer + version-chain expectations.
- [x] Add API tests for attach idempotency/no-side-effect replay behavior (if idempotency key provided).
- [x] Add unit tests for ownership scoping and transactional attach semantics.
- [x] Re-verify `/openapi.json` includes:
- [x] `/jobs/{jobId}/screenshots/uploads` (`201/404`)
- [x] `/jobs/{jobId}/screenshots/uploads/{uploadId}/confirm` (`200/404`)
- [x] `/anchors/{anchorId}/attach-upload` (`200/404`)
- [x] with expected request/response schema refs.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

## Dev Notes

### Developer Context Section

- Story 5.3 completed soft-delete + deterministic fallback on version chains; Story 5.4 extends lifecycle coverage with uploaded-image ingest and attach semantics.
- Story 5.4 is part of Task 13 lifecycle scope (`replace/delete/upload/attach`) and must remain contract-first with no new API shape beyond OpenAPI.
- Attachment behavior must preserve the same anchor version-chain invariants already established by replace/delete stories.

### Technical Requirements

- Endpoints in scope:
- `POST /jobs/{jobId}/screenshots/uploads`
- `POST /jobs/{jobId}/screenshots/uploads/{uploadId}/confirm`
- `POST /anchors/{anchorId}/attach-upload`
- Contract behavior from OpenAPI:
- uploads ticket `POST`: `201` (`CustomUploadTicket`), `404` (no-leak).
- uploads confirm `POST`: `200` (`ConfirmCustomUploadResponse`), `404` (no-leak).
- attach-upload `POST`: `200` (`ScreenshotAnchor`), `404` (no-leak).
- Schema constraints from OpenAPI:
- `CreateCustomUploadRequest`: `filename`, `mime_type`, `size_bytes`, `checksum_sha256`; MIME enum excludes SVG.
- `ConfirmCustomUploadRequest`: `mime_type`, `size_bytes`, `checksum_sha256`, `width`, `height`.
- `AttachUploadedAssetRequest`: `upload_id`, `instruction_version_id`, optional `idempotency_key`.
- `CustomUploadTicket`: must include `upload_id`, `upload_url`, `expires_at`, `max_size_bytes`, `allowed_mime_types`.

### Architecture Compliance

- `spec/` is read-only source of truth.
- Keep route handlers thin; enforce ownership, validation, persistence, and transactional attach logic in service/repository layers.
- Preserve no-existence-leak behavior (`404`) for unauthorized/missing resources.
- Preserve artifact discipline:
- raw artifacts remain immutable.
- uploaded screenshots are derived/versioned assets with explicit linkage and active-pointer management.
- Signed upload URLs must be time-limited and policy-bound.

### Library & Framework Requirements

- FastAPI + Pydantic remain contract authority for request/response modeling.
- Reuse screenshot anchor/asset persistence patterns from Stories 5.1-5.3 (version chain, `active_asset_id`, owner-scoped lookups).
- Reuse existing OpenAPI shaping/assertion patterns in `app/main.py` and `test_auth_middleware.py`.
- No new dependencies expected.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/schemas/job.py` (upload/confirm/attach request-response models and any supporting schema extensions)
- `apps/api/app/routes/jobs.py` (add upload ticket, confirm, and attach handlers)
- `apps/api/app/services/jobs.py` (owner-scoped ticket/confirm/attach business logic)
- `apps/api/app/repositories/memory.py` (upload ticket persistence, confirmation state, attach transactional version-chain updates)
- `apps/api/app/main.py` (OpenAPI response-code allowlist + schema shaping for upload/confirm/attach paths)
- `apps/api/tests/test_jobs_ownership.py` (API/unit tests for upload/confirm/attach lifecycle and no-leak behavior)
- `apps/api/tests/test_auth_middleware.py` (OpenAPI path/response/schema assertions for new routes)

### Testing Requirements

- Validate ticket creation returns `201` with contract-required ticket fields.
- Validate ticket creation is owner-scoped and no-leak `404` for unknown/cross-owner job.
- Validate confirm returns `200` with `asset` payload and persisted metadata fields.
- Validate confirm enforces MIME allowlist and rejects SVG by default.
- Validate confirm enforces minimum/valid size and dimensions; invalid payloads must not mutate state.
- Validate attach returns `200` and updates anchor `active_asset_id` with correct version-chain linkage (`previous_asset_id`, version increment).
- Validate attach no-leak `404` for missing/cross-owner anchor or unknown upload.
- Validate attach idempotency behavior (if `idempotency_key` provided by contract/story policy) without duplicate version creation.
- Validate `/openapi.json` contract alignment for the three new paths and schema refs.
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Story 5.3 established:
- soft-delete state on assets (`is_deleted`) with deterministic fallback traversal across `previous_asset_id`.
- strict owner/no-leak behavior in screenshot lifecycle routes.
- OpenAPI contract shaping discipline and explicit schema assertions for screenshot endpoints.
- Story 5.4 should build directly on these patterns and avoid introducing parallel data models for uploads.

### Git Intelligence Summary

- Recent backend work emphasizes minimal-diff, contract-first changes with:
- thin route handlers + service-owned logic
- deterministic repository updates
- no-side-effect assertions in tests
- OpenAPI schema/reference enforcement in `app/main.py` plus middleware tests
- Maintain the same style for Story 5.4 to minimize regression risk.

### Project Structure Notes

- No standalone architecture artifact exists in `_bmad-output/planning-artifacts/`; use `epics.md`, `prd.md`, OpenAPI, and current screenshot lifecycle implementation as guardrails.
- Keep Story 5.4 focused on upload/confirm/attach only; annotation and anchor persistence policy are covered in Stories 5.5 and 5.6.

### References

- `spec/api/openapi.yaml` (`CreateCustomUploadRequest`, `CustomUploadTicket`, `ConfirmCustomUploadRequest`, `ConfirmCustomUploadResponse`, `AttachUploadedAssetRequest`, `/jobs/{jobId}/screenshots/uploads`, `/jobs/{jobId}/screenshots/uploads/{uploadId}/confirm`, `/anchors/{anchorId}/attach-upload`)
- `_bmad-output/planning-artifacts/epics.md` (Epic 5, Story 5.4)
- `_bmad-output/planning-artifacts/prd.md` (FR-035 and screenshot lifecycle constraints)
- `spec/acceptance/tasks_codex_v1.md` (Task 13 upload/attach lifecycle intent)
- `_bmad-output/project-context.md` (contract-first API, artifact discipline, no-leak policy, signed URL constraints)
- `_bmad-output/implementation-artifacts/5-3-soft-delete-screenshot-asset-and-resolve-active-fallback.md`
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
- `_bmad-output/implementation-artifacts/5-3-soft-delete-screenshot-asset-and-resolve-active-fallback.md`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/schemas/job.py`
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_auth_middleware.py`

### Completion Notes List

- 2026-03-01: Created Story 5.4 artifact with AC-mapped tasks for upload ticket, confirm, and attach flows.
- 2026-03-01: Captured MIME/size/checksum/dimension validation and explicit SVG-rejection guardrails for confirm behavior.
- 2026-03-01: Captured transactional attach versioning requirements (`previous_asset_id`, version increment, anchor `active_asset_id` update).
- 2026-03-01: Implemented upload ticket, confirm-upload, and attach-upload route/service/repository flows with no-leak `404` behavior and contract-safe status sets.
- 2026-03-01: Added OpenAPI shaping and request-validation handling for custom upload endpoints, including schema refs for request/response bodies.
- 2026-03-01: Added API and unit coverage for ticket creation, confirmation metadata persistence, SVG/default invalid-path rejection, attach versioning, and attach idempotency.
- 2026-03-01: Verified `make lint`, `make test`, and `make check` all pass in `apps/api`.

### File List

- `_bmad-output/implementation-artifacts/5-4-upload-custom-image-via-signed-url-and-confirm-attach.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/schemas/job.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_jobs_ownership.py`

### Change Log

- 2026-03-01: Created Story 5.4 artifact and moved sprint status from `backlog` to `ready-for-dev`.
- 2026-03-01: Implemented Story 5.4 upload/confirm/attach API workflow and added AC-mapped test coverage.
- 2026-03-01: Moved Story 5.4 status from `ready-for-dev` to `review` after full verification.
- 2026-03-02: Applied code-review remediations (signed upload URL integrity checks, SHA-256 checksum format validation, safer upload object URI handling) and moved status to `done`.
