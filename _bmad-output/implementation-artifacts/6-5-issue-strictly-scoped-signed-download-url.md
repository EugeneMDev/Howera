# Story 6.5: Issue Strictly Scoped Signed Download URL

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want a secure signed download URL for completed exports,
so that I can retrieve deliverables safely.

## Acceptance Criteria

1. Given export state is `SUCCEEDED`, when download URL is issued, then URL is signed with strict resource scoping to that artifact only, URL TTL follows policy (for example 15 minutes, or contract/config value), and credential material is never logged.
2. Given export state is not `SUCCEEDED`, when export status is requested, then API returns `200` with export state details but without signed download URL fields, and no signed URL is issued.

## Tasks / Subtasks

- [x] Implement signed download URL issuance for completed exports (AC: 1)
- [x] Add deterministic signing logic that scopes URL access to one export artifact (`export_id`-scoped resource binding only).
- [x] Apply explicit expiry policy for issued URLs (default policy target: 15 minutes, configurable if needed).
- [x] Ensure issued URL metadata is returned via existing `Export.download_url` and `Export.download_url_expires_at` fields.
- [x] Enforce non-`SUCCEEDED` retrieval behavior without URL issuance (AC: 2)
- [x] Keep `GET /exports/{exportId}` contract-safe for non-`SUCCEEDED` states by returning `200` export status and omitting signed download fields.
- [x] Preserve existing owner-scoped no-leak semantics (`404`) for missing/cross-owner export IDs.
- [x] Keep status polling behavior read-only (no export/job mutation side effects during URL issuance checks).
- [x] Harden security and logging guarantees for signed URLs (AC: 1)
- [x] Ensure signature/credential query parameters are never written to logs.
- [x] Restrict any operational logging to safe identifiers only (for example hashed/correlation identifiers).
- [x] Add AC-mapped API/unit/OpenAPI coverage (AC: 1, 2)
- [x] Add tests asserting `SUCCEEDED` export retrieval includes signed URL + expiry and that TTL falls within policy bounds.
- [x] Add tests asserting URL scope cannot drift across exports (resource binding is export-specific).
- [x] Add tests asserting non-`SUCCEEDED` export retrieval omits signed URL fields.
- [x] Add tests asserting no-leak `404` parity remains identical for missing vs unauthorized export IDs.
- [x] Add tests/assertions ensuring OpenAPI contract for `/exports/{exportId}` remains `200/404` with `Export`/`NoLeakNotFoundError` schemas.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

### Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Move export download signing key out of source constants into secure runtime configuration/secret management (`apps/api/app/repositories/memory.py:75`).
- [x] [AI-Review][MEDIUM] Make download URL host and TTL policy configurable via settings/environment rather than hard-coded values (`apps/api/app/repositories/memory.py:74`, `apps/api/app/repositories/memory.py:76`).
- [x] [AI-Review][MEDIUM] Enforce export-state precondition at URL issuance boundary (repository helper) to prevent accidental signing from non-`SUCCEEDED` call sites (`apps/api/app/repositories/memory.py:714`).
- [x] [AI-Review][LOW] Align timestamp precision between signed epoch and returned `download_url_expires_at` to avoid sub-second expiry drift (`apps/api/app/repositories/memory.py:722`, `apps/api/app/repositories/memory.py:2545`).
- [x] [AI-Review][HIGH] Restore clean-shell verification by ensuring `make test` does not fail at import time due to required `callback_secret` when `app = create_app()` loads settings (`apps/api/app/main.py:757`, `apps/api/app/main.py:854`, `apps/api/Makefile:7`).

## Dev Notes

### Developer Context Section

- Story 6.4 implemented owner-scoped `GET /exports/{exportId}` retrieval with no-leak `404` and read-only polling semantics.
- Story 6.3 implemented export lifecycle finalization and provenance freeze (`provenance_frozen_at`) on `SUCCEEDED`.
- Story 6.5 extends retrieval semantics by issuing secure, time-limited download URLs only for completed exports.
- Keep strict contract-first boundaries: no new endpoint surface or undocumented response status codes in this story.

### Technical Requirements

- Endpoint in scope:
- `GET /exports/{exportId}`
- Contract behavior from OpenAPI:
- `200` returns `Export`.
- `404` returns `NoLeakNotFoundError` (missing and unauthorized are indistinguishable).
- `Export` already contains `download_url` and `download_url_expires_at` fields.
- Signed URL requirements:
- URL issuance allowed only when export status is `SUCCEEDED`.
- URL must be strictly scoped to that export artifact (no cross-export or broad bucket-level access semantics).
- URL must be time-limited; policy target is 15 minutes unless config defines another value.
- Non-`SUCCEEDED` behavior:
- Preserve current contract-safe behavior by returning `200` export status without download URL fields.
- Do not introduce additional response codes unless OpenAPI contract is changed in a separate task.
- Security requirement:
- Signature/credential material must not be logged.

### Architecture Compliance

- `spec/` remains read-only source of truth.
- Preserve thin route handlers; signing/issuance logic belongs in service/repository/core helper layers.
- Maintain no-existence-leak behavior and owner scoping for export retrieval.
- Preserve deterministic read behavior: retrieval should not mutate export/job lifecycle state.
- Follow existing secure logging boundary practices (`safe_log_identifier` and redaction discipline).

### Library & Framework Requirements

- FastAPI + Pydantic remain contract authority.
- Prefer reuse of existing signed-URL/security patterns already implemented for screenshot custom upload tickets in the in-memory repository.
- No new external dependencies expected for v1 implementation.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/services/jobs.py` (export retrieval URL issuance behavior and non-`SUCCEEDED` policy)
- `apps/api/app/repositories/memory.py` (signing helper/policy utilities and deterministic scoping support as needed)
- `apps/api/app/core/config.py` (TTL policy setting, only if configuration-driven policy is introduced)
- `apps/api/app/main.py` (OpenAPI shaping remains aligned; update only if needed for existing contract references)
- `apps/api/tests/test_jobs_ownership.py` (API/unit coverage for signed URL issuance, gating, no-leak, read-only behavior)
- `apps/api/tests/test_auth_middleware.py` (OpenAPI contract assertions for `/exports/{exportId}`)

### Testing Requirements

- Validate `SUCCEEDED` export retrieval returns signed `download_url` and `download_url_expires_at`.
- Validate issued URL scope is export-specific and deterministic for the requested export.
- Validate `REQUESTED`, `RUNNING`, and `FAILED` retrieval responses do not include signed download URL fields.
- Validate missing and cross-owner retrieval remain identical no-leak `404` responses.
- Validate retrieval-side checks do not mutate job/export write counters.
- Validate log output does not contain raw URL signatures or credential tokens.
- Validate `/openapi.json` remains aligned for `/exports/{exportId}` (`200/404`, `Export`/`NoLeakNotFoundError`).
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Story 6.4 intentionally deferred signed URL issuance and currently returns URL fields only when present in persisted export data.
- Story 6.4 also established read-only retrieval assertions and no-leak ownership behavior that must be preserved.
- Story 6.3 ensured `SUCCEEDED` is the completion boundary; signed URL issuance should key off that deterministic state.
- Story 5.4 introduced secure signed URL patterns (expiry + signature integrity) for uploads; reuse those hardening patterns where applicable.

### Git Intelligence Summary

- Recent Epic 6 implementation patterns favor minimal diffs, deterministic behavior, and explicit no-leak/OpenAPI assertions.
- Existing export behavior is centralized in `jobs` service + in-memory repository; extending this path is lower-risk than introducing new layers.
- Keep test changes focused and additive (no broad refactors) to preserve regression visibility.

### Project Structure Notes

- No standalone architecture artifact is present in `_bmad-output/planning-artifacts/`; derive constraints from OpenAPI, PRD, epic definitions, project context, and current implementation.
- Keep Story 6.5 strictly scoped to signed download URL issuance policy on existing export retrieval.
- Defer canonical export audit-event enhancements to Story 6.6.

### References

- `spec/api/openapi.yaml` (`/exports/{exportId}`, `Export.download_url`, `Export.download_url_expires_at`)
- `_bmad-output/planning-artifacts/epics.md` (Epic 6, Story 6.5)
- `_bmad-output/planning-artifacts/prd.md` (FR-027, FR-028, FR-030)
- `spec/acceptance/v1_mvp.md` (download URL visibility on `SUCCEEDED`)
- `spec/acceptance/tasks_codex_v1.md` (Task 15 export status/download URL policy)
- `_bmad-output/project-context.md` (contract-first constraints, security baseline, signed URL policy)
- `_bmad-output/implementation-artifacts/6-3-execute-export-fsm-and-freeze-provenance-on-success.md`
- `_bmad-output/implementation-artifacts/6-4-retrieve-export-status-by-export-id.md`
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
- `_bmad-output/implementation-artifacts/6-4-retrieve-export-status-by-export-id.md`

### Completion Notes List

- 2026-03-04: Created Story 6.5 artifact from sprint backlog with AC-mapped tasks for strictly scoped signed download URL issuance.
- 2026-03-04: Captured export retrieval contract constraints from OpenAPI and linked security requirements from PRD/project context.
- 2026-03-04: Incorporated prior-story guardrails (6.3 lifecycle determinism and 6.4 no-leak/read-only retrieval) to prevent regressions.
- 2026-03-04: Ultimate context engine analysis completed - comprehensive developer guide created.
- 2026-03-04: Implemented export-scoped signed download URL issuance for `SUCCEEDED` exports via repository signing helper and service-layer response binding.
- 2026-03-04: Added AC coverage for URL scope/signature/TTL policy, non-`SUCCEEDED` URL omission, no-leak parity, and read-only retrieval counters.
- 2026-03-04: Added security regression coverage to ensure export retrieval does not log signed URL credentials.
- 2026-03-04: Verified quality gates in `apps/api` with `make lint`, `make test`, and `make check` (all passing; `194` tests).
- 2026-03-04: Code review run identified security/policy hardening gaps; story moved back to `in-progress` with AI follow-up action items.
- 2026-03-04: Remediated all AI review findings by moving signing/TTL/host policy to runtime settings, enforcing `SUCCEEDED` at issuance boundary, and aligning expiry precision.
- 2026-03-04: Re-ran quality gates in `apps/api` with `make lint`, `make test`, and `make check` (all passing; `198` tests).
- 2026-03-04: Re-review identified clean-shell test regression (`make test` requires externally pre-set `HOWERA_CALLBACK_SECRET` due import-time settings resolution); story moved to `in-progress`.
- 2026-03-04: Fixed clean-shell verification regression by making `apps/api/Makefile` inject a deterministic test callback secret when missing (`HOWERA_CALLBACK_SECRET=${HOWERA_CALLBACK_SECRET:-test-callback-secret}`), preserving existing env override behavior.
- 2026-03-04: Re-ran `make lint`, `make test`, and `make check` in `apps/api` without pre-setting env vars (all passing; `198` tests).
- 2026-03-05: Final code re-review found no remaining high/medium/low defects for Story 6.5 scope; quality gates remained green and story moved to `done`.

### File List

- `_bmad-output/implementation-artifacts/6-5-issue-strictly-scoped-signed-download-url.md`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/services/jobs.py`
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/Makefile`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-04: Created Story 6.5 artifact and moved sprint status from `backlog` to `ready-for-dev`.
- 2026-03-04: Implemented Story 6.5 signed download URL policy/scoping with AC-mapped tests and moved story/sprint status to `review`.
- 2026-03-04: Code review (changes requested) added AI review follow-ups and moved story/sprint status to `in-progress`.
- 2026-03-04: Completed remediation for all code-review findings and moved story/sprint status back to `review`.
- 2026-03-04: Re-review found a clean-shell verification regression and moved story/sprint status back to `in-progress`.
- 2026-03-04: Fixed clean-shell test gate regression via `Makefile` test-env injection and moved story/sprint status back to `review`.
- 2026-03-05: Final re-review approved with no remaining findings; story/sprint status moved to `done`.

## Senior Developer Review (AI)

### Reviewer

- `Codex` (AI Senior Developer Reviewer)
- Date: 2026-03-04

### Outcome

- Changes Requested

### Findings Summary

- High: 1
- Medium: 2
- Low: 1

### Findings and Recommended Fixes

- [x] [HIGH] Signing secret is hard-coded in source instead of runtime secret configuration (`_EXPORT_DOWNLOAD_SIGNING_KEY`), violating secure secret-management baseline.  
  Evidence: `apps/api/app/repositories/memory.py:75`
- [x] [MEDIUM] Download URL host and TTL are hard-coded constants, reducing policy portability across environments and making TTL policy changes code-only.  
  Evidence: `apps/api/app/repositories/memory.py:74`, `apps/api/app/repositories/memory.py:76`
- [x] [MEDIUM] `issue_export_download_url(...)` does not enforce `SUCCEEDED` state at issuance boundary, relying entirely on service call-site discipline (defense-in-depth gap).  
  Evidence: `apps/api/app/repositories/memory.py:714`
- [x] [LOW] Returned `download_url_expires_at` keeps sub-second precision while signed `expires` uses integer epoch, creating up-to-1s effective TTL mismatch.  
  Evidence: `apps/api/app/repositories/memory.py:722`, `apps/api/app/repositories/memory.py:2545`

### Re-Review (AI) - 2026-03-04

#### Outcome

- Changes Requested

#### Summary

- Prior security/policy hardening findings are resolved.
- One regression remains: `make test` fails in a clean shell because `create_app()` now resolves required settings during module import.

#### Severity Breakdown

- High: 1
- Medium: 0
- Low: 0

#### Action Items

- [x] [HIGH] Ensure verification gates run cleanly without requiring manual pre-export of `HOWERA_CALLBACK_SECRET`; either avoid import-time settings resolution dependency for test discovery or make the project test command provide required env deterministically.  
  Evidence: `apps/api/app/main.py:757`, `apps/api/app/main.py:854`, `apps/api/Makefile:7`

#### Resolution Update (Dev) - 2026-03-04

- Implemented deterministic test env injection in `apps/api/Makefile` (`HOWERA_CALLBACK_SECRET=${HOWERA_CALLBACK_SECRET:-test-callback-secret}`) so clean-shell `make test`/`make check` run without manual pre-export.
- Re-verified quality gates in `apps/api`: `make lint`, `make test`, `make check` (all passing; `198` tests).

### Final Re-Review (AI) - 2026-03-05

#### Outcome

- Approved

#### Summary

- No new defects were identified in Story 6.5 scope.
- Signed URL security/policy hardening and clean-shell gate regression remediation remain effective.
- Verification gates are green (`make lint`, `make test`, `make check`).

#### Severity Breakdown

- High: 0
- Medium: 0
- Low: 0

#### Residual Risk

- Remaining risk is low and primarily operational (future environment/config drift); current automated coverage for status-gated URL issuance, no-leak behavior, and clean-shell test execution is in place.
