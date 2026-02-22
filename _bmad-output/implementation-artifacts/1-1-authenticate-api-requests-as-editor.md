# Story 1.1: Authenticate API Requests as Editor

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want authenticated API requests to resolve my identity,
so that protected operations are executed only for valid users.

## Acceptance Criteria

1. Given a request to a protected write endpoint without a valid bearer token, when the request is processed, then the API returns `401 Unauthorized` and no domain write operation is executed.
2. Given a request with a valid token containing editor identity, when the request is processed, then the API resolves `user_id` into request context and downstream handlers can enforce ownership checks.

## Tasks / Subtasks

- [ ] Implement auth dependency and token verifier adapter (AC: 1, 2)
- [ ] Add adapter interface and Firebase verifier implementation under `apps/api/app/adapters/auth/`.
- [ ] Parse `Authorization: Bearer <jwt>` and validate token signature and claims.
- [ ] Normalize verifier output to internal auth principal data (`user_id`, role).
- [ ] Add request-scoped auth context for routes (AC: 2)
- [ ] Add dependency function in `apps/api/app/routes/dependencies.py` to return authenticated principal.
- [ ] Ensure dependency fails fast before any service/domain write logic executes.
- [ ] Protect editor-facing write endpoints with bearer auth dependency (AC: 1, 2)
- [ ] Apply dependency on write routes in current scope (`POST /projects`, `POST /projects/{projectId}/jobs`, and other editor-write routes when added).
- [ ] Keep `/internal/jobs/{jobId}/status` on `X-Callback-Secret` auth path only (Story 1.4 scope).
- [ ] Return contract-compatible `401` response payload on auth failures.
- [ ] Wire auth-related settings and secure logging (AC: 1, 2)
- [ ] Add config for Firebase verification input (project/audience) and test-only mock path.
- [ ] Do not log raw JWT tokens, callback secrets, or transcript content.
- [ ] Add tests for unauthorized and authorized behavior (AC: 1, 2)
- [ ] Add API tests for missing/invalid token -> `401` and no side effects.
- [ ] Add API tests for valid token -> resolved `user_id` available to downstream handlers.
- [ ] Add unit tests for dependency/verifier normalization and failure mapping.

## Dev Notes

### Developer Context Section

- This story establishes authentication baseline only. Resource ownership authorization is handled by subsequent stories, but `user_id` propagation must be in place now.
- The codebase is scaffold-level in `apps/api/app/`; keep implementation narrow and incremental.

### Technical Requirements

- Enforce bearer authentication on editor-facing protected write endpoints per OpenAPI contract.
- Unauthorized requests must return `401` and must not mutate state.
- Valid requests must resolve and propagate authenticated `user_id` into request context.
- Keep route handlers thin; no business logic in routes.

### Architecture Compliance

- `spec/` is read-only; code must conform to `spec/api/openapi.yaml`.
- External auth verification must be isolated in adapter layer (no direct provider calls in route/business logic).
- Maintain provider swappability by coding to internal auth interface.
- Do not add new endpoints, fields, or status codes outside contract.

### Library & Framework Requirements

- FastAPI dependency injection for auth context and route protection.
- Pydantic models for internal auth principal normalization where used.
- If Firebase Admin SDK is introduced, confine it to adapter implementation.

### File Structure Requirements

- Suggested file targets for this story:
- `apps/api/app/adapters/auth/base.py`
- `apps/api/app/adapters/auth/firebase_auth.py`
- `apps/api/app/routes/dependencies.py`
- `apps/api/app/schemas/auth.py`
- `apps/api/tests/test_auth_middleware.py`
- Keep business/domain logic in `services/` and `domain/`, not in `routes/`.

### Testing Requirements

- Add tests that map directly to ACs before implementation completion.
- Required checks:
- Missing `Authorization` header returns `401`.
- Malformed/invalid bearer token returns `401`.
- Valid bearer token permits request and exposes `user_id`.
- Unauthorized write calls do not trigger domain write side effects.
- Use deterministic fake/mocked auth adapter behavior in tests.

### Project Structure Notes

- Story scope excludes callback-secret authentication (`X-Callback-Secret`), which belongs to Story 1.4.
- If endpoint implementations are still stubs, add only minimal auth plumbing and test hooks needed for later story execution.

### References

- `spec/api/openapi.yaml` (global bearer security, project/job endpoint contracts, internal callback security override)
- `_bmad-output/planning-artifacts/epics.md` (Epic 1, Story 1.1 ACs)
- `_bmad-output/planning-artifacts/prd.md` (authenticated write endpoints, ownership boundaries)
- `_bmad-output/project-context.md` (architectural invariants, v1 security model)
- `spec/acceptance/tasks_codex_v1.md` (Task 04 Firebase Auth Middleware, route thinness rule)

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- No architecture artifact was available in planning artifacts; story guardrails were derived from OpenAPI, PRD, epics, and project context.

### File List

- `_bmad-output/implementation-artifacts/1-1-authenticate-api-requests-as-editor.md`
