# Story 7.2: Restore Firebase Session and Protect Workspace Routes

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want valid sessions restored automatically and protected routes guarded,
so that I can resume work safely without reimplementing auth per screen.

## Acceptance Criteria

1. Given a user returns with a persisted Firebase session, when the app initializes, then Firebase restores the session and `currentUser` becomes available and protected routes resume with bearer-authenticated API access.
2. Given a user is unauthenticated, when they access a protected workspace route, then they are redirected into the Firebase sign-in flow and no protected API calls execute until auth completes.

## Tasks / Subtasks

- [x] Add Firebase web auth initialization and session-restore flow in `apps/web`.
- [x] Add auth provider and hooks that expose authenticated user and loading state.
- [x] Guard workspace routes so unauthenticated users are redirected before protected queries run.
- [x] Inject bearer tokens into the shared API client from `currentUser.getIdToken()`.
- [x] Add re-auth and recoverable auth-failure UX for expired or rejected sessions.
- [x] Add unit coverage for protected-route redirect helpers, token injection, and unauthorized recovery behavior.

## Dev Notes

### Developer Context Section

- Backend bearer-auth behavior is already established by Story 1.1.
- Frontend auth must follow the Firebase session approach locked in `_bmad-output/planning-artifacts/epics-frontend-bmad.md`.
- Route protection belongs in shared auth and routing primitives, not inside individual pages.
- Current implementation adds a top-level `AuthProvider`, route-group protection for `(workspace)` routes, a dedicated `/sign-in` page, Firebase redirect-based Google sign-in, and shared unauthorized recovery surfaced through the API client.
- Protected API clients now request bearer tokens through the auth provider rather than reading session state ad hoc inside feature pages.

### Technical Requirements

- Use Firebase Web SDK for session restore and sign-in flow.
- Avoid firing protected project/job/instruction queries before auth is ready.
- Keep auth header logic inside the shared API client layer.
- Provide user-safe `401` recovery without exposing raw tokens.
- Keep the sign-in route safe for App Router static prerendering by wrapping `useSearchParams()` usage in a `Suspense` boundary.

### File Structure Requirements

- Primary expected touch points:
- `apps/web/src/features/auth/`
- `apps/web/src/shared/api/`
- `apps/web/src/app/(workspace)/`
- `apps/web/src/middleware/` or route-level guard utilities if needed
- `apps/web/tests/`

### Testing Requirements

- Verify persisted session restoration.
- Verify unauthenticated users do not trigger protected API requests.
- Verify valid session requests include bearer auth automatically.
- Verify auth failure surfaces re-auth UI rather than silent failure.
- Final verification target: `cd apps/web && make check`.

### References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `spec/api/openapi.yaml`
- `_bmad-output/implementation-artifacts/1-1-authenticate-api-requests-as-editor.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `spec/api/openapi.yaml`
- `_bmad-output/implementation-artifacts/1-1-authenticate-api-requests-as-editor.md`

### Completion Notes List

- 2026-03-24: Created Story 7.2 artifact with Firebase session-restore and protected-routing scope.
- 2026-03-24: Captured bearer-token injection and recoverable auth-failure requirements for frontend implementation.
- 2026-03-24: Added Firebase client initialization, redirect-based Google sign-in, shared auth context, and session restore via `onIdTokenChanged`.
- 2026-03-24: Protected `(workspace)` routes with an auth guard and added a dedicated `/sign-in` route that preserves safe internal return paths.
- 2026-03-24: Wired bearer-token lookup and centralized `401` recovery into the shared API client through `AppProviders`.
- 2026-03-24: Added unit tests for redirect normalization and API token/unauthorized handling, then passed `make lint`, `make test`, `make typecheck`, `make build`, and `make check` in `apps/web`.

### File List

- `_bmad-output/implementation-artifacts/7-2-restore-firebase-session-and-protect-workspace-routes.md`
- `_bmad-output/implementation-artifacts/frontend-sprint-status.yaml`
- `apps/web/src/app/(workspace)/layout.tsx`
- `apps/web/src/app/layout.tsx`
- `apps/web/src/app/sign-in/page.tsx`
- `apps/web/src/features/auth/auth-provider.tsx`
- `apps/web/src/features/auth/firebase-client.ts`
- `apps/web/src/features/auth/redirect.ts`
- `apps/web/src/features/auth/components/auth-guard.tsx`
- `apps/web/src/features/auth/components/auth-status-card.tsx`
- `apps/web/src/features/auth/components/sign-in-screen.tsx`
- `apps/web/src/shared/api/client.ts`
- `apps/web/src/shared/providers/app-providers.tsx`
- `apps/web/src/shared/ui/async-state.tsx`
- `apps/web/tests/unit/api-client.test.ts`
- `apps/web/tests/unit/auth-redirect.test.ts`

### Change Log

- 2026-03-24: Created Story 7.2 artifact and moved frontend story status from `backlog` to `ready-for-dev`.
- 2026-03-24: Implemented Firebase session restore, protected workspace route guarding, bearer token injection, and recoverable auth-failure UX in `apps/web`.
- 2026-03-24: Added auth-focused unit coverage, fixed Next.js prerender requirements for `/sign-in`, passed `make check`, and moved Story 7.2 to `done`.
