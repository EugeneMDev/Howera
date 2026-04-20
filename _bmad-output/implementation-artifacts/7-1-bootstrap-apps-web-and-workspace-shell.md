# Story 7.1: Bootstrap `apps/web` and Workspace Shell

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want a stable frontend shell with shared layout and state primitives,
so that all product flows feel consistent and implementation can scale.

## Acceptance Criteria

1. Given the frontend app is initialized, when a user opens workspace routes, then a shared app shell renders navigation, workspace, and context panel regions and shared loading, empty, and error states are available for feature teams.
2. Given frontend infrastructure is configured, when developers add new screens, then shared API client, query provider, and design tokens are reused and environment-driven API/Firebase configuration is already in place.

## Tasks / Subtasks

- [x] Bootstrap `apps/web` with Next.js App Router, TypeScript, and app-local scripts.
- [x] Add local frontend toolchain files: `package.json`, `tsconfig.json`, `next.config.ts`, `postcss.config.mjs`, `eslint.config.mjs`, `next-env.d.ts`, and `Makefile`.
- [x] Add root app layout, workspace route group, and default redirect into the workspace shell.
- [x] Add a shared workspace shell with navigation, main content, and context panel regions.
- [x] Add static scaffold pages for `projects`, `jobs`, and `instructions` to prove the shell composition.
- [x] Add tokenized styling and reusable UI primitives for panels, buttons, status chips, and class composition.
- [x] Add global styling and centralized design tokens for color, typography, spacing, radii, and focus behavior.
- [x] Add env-driven runtime config parsing and `.env` example for frontend public settings.
- [x] Add shared frontend providers for runtime config, API client access, and query-state invalidation scaffolding.
- [x] Add shared loading, empty, and error state primitives and wire them into scaffold pages.
- [x] Add shell render smoke tests for layout regions and base button behavior.
- [x] Add runtime-config and async-state unit tests for foundation modules.
- [x] Add Node/Next build artifacts to repo ignore rules.
- [x] Install frontend dependencies and pass `make lint`, `make test`, and `make check`.

## Dev Notes

### Developer Context Section

- Frontend architecture is defined in `_bmad-output/planning-artifacts/architecture.md`.
- UX requires a three-zone shell and token-first styling from `_bmad-output/planning-artifacts/ux-design-specification.md`.
- This story establishes the base that Stories 7.2 through 11.4 build on.
- Current implementation includes shell, tokens, primitives, preview routes, env parsing, shared providers, API-client scaffolding, and reusable async-state surfaces.
- Story 7.1 is complete and verified locally in `apps/web`.

### Technical Requirements

- Use Next.js App Router in `apps/web`.
- Keep the shell persistent across workspace routes.
- Centralize theme tokens, shared primitives, and environment-driven config.
- Do not introduce frontend-only business logic that bypasses backend contract behavior.
- Keep later stories building on the shared providers and state primitives introduced here rather than reintroducing ad hoc page-local scaffolding.

### File Structure Requirements

- Primary expected touch points:
- `apps/web/package.json`
- `apps/web/Makefile`
- `apps/web/.env.example`
- `apps/web/next.config.ts`
- `apps/web/postcss.config.mjs`
- `apps/web/eslint.config.mjs`
- `apps/web/tsconfig.json`
- `apps/web/src/app/layout.tsx`
- `apps/web/src/app/(workspace)/layout.tsx`
- `apps/web/src/app/(workspace)/projects/page.tsx`
- `apps/web/src/app/(workspace)/jobs/page.tsx`
- `apps/web/src/app/(workspace)/instructions/page.tsx`
- `apps/web/src/features/shell/`
- `apps/web/src/shared/api/`
- `apps/web/src/shared/config/`
- `apps/web/src/shared/providers/`
- `apps/web/src/shared/lib/`
- `apps/web/src/shared/ui/`
- `apps/web/src/shared/styles/`
- `apps/web/tests/`

### Testing Requirements

- Add shell render smoke tests.
- Verify route-group shell composition and shared primitives.
- Verify local commands for lint, test, typecheck, and build are wired.
- Final verification target: `cd apps/web && make check`.

### References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/implementation-artifacts/frontend-sprint-status.yaml`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/implementation-artifacts/frontend-sprint-status.yaml`

### Completion Notes List

- 2026-03-24: Created Story 7.1 artifact with AC-mapped frontend foundation tasks and implementation guardrails.
- 2026-03-24: Bootstrapped `apps/web` with Next.js App Router, TypeScript config, local frontend scripts, ESLint, PostCSS, and `Makefile` commands.
- 2026-03-24: Implemented the shared workspace shell, shell navigation config, route-group layout, and static preview pages for `projects`, `jobs`, and `instructions`.
- 2026-03-24: Added centralized design tokens, global styles, base UI primitives (`Button`, `Panel`, `StatusPill`), and a `cn` utility.
- 2026-03-24: Added env-driven frontend runtime parsing, `.env.example`, shared providers, API-client scaffolding, and reusable loading-empty-error state primitives.
- 2026-03-24: Added unit tests covering shell regions, default button safety, runtime config parsing, and async-state rendering.
- 2026-03-24: Installed frontend dependencies locally, generated `package-lock.json`, and passed `make lint`, `make test`, and `make check` in `apps/web`.
- 2026-03-24: Added `outputFileTracingRoot` in Next config so local production builds use the repository root rather than inferring an unrelated parent lockfile.

### File List

- `.gitignore`
- `_bmad-output/implementation-artifacts/7-1-bootstrap-apps-web-and-workspace-shell.md`
- `apps/web/Makefile`
- `apps/web/.env.example`
- `apps/web/eslint.config.mjs`
- `apps/web/next-env.d.ts`
- `apps/web/next.config.ts`
- `apps/web/package-lock.json`
- `apps/web/package.json`
- `apps/web/postcss.config.mjs`
- `apps/web/src/app/(workspace)/instructions/page.tsx`
- `apps/web/src/app/(workspace)/jobs/page.tsx`
- `apps/web/src/app/(workspace)/layout.tsx`
- `apps/web/src/app/(workspace)/projects/page.tsx`
- `apps/web/src/app/globals.css`
- `apps/web/src/app/layout.tsx`
- `apps/web/src/app/page.tsx`
- `apps/web/src/features/shell/components/workspace-shell-frame.tsx`
- `apps/web/src/features/shell/components/workspace-shell.tsx`
- `apps/web/src/features/shell/config/navigation.ts`
- `apps/web/src/shared/api/client.ts`
- `apps/web/src/shared/api/errors.ts`
- `apps/web/src/shared/config/runtime.ts`
- `apps/web/src/shared/lib/cn.ts`
- `apps/web/src/shared/providers/app-providers.tsx`
- `apps/web/src/shared/styles/tokens.css`
- `apps/web/src/shared/ui/async-state.tsx`
- `apps/web/src/shared/ui/button.tsx`
- `apps/web/src/shared/ui/panel.tsx`
- `apps/web/src/shared/ui/status-pill.tsx`
- `apps/web/tests/unit/async-state.test.tsx`
- `apps/web/tests/unit/runtime-config.test.ts`
- `apps/web/tests/unit/workspace-shell.test.tsx`
- `apps/web/tsconfig.json`

### Change Log

- 2026-03-24: Created Story 7.1 artifact and moved frontend story status from `backlog` to `in-progress`.
- 2026-03-24: Implemented the initial `apps/web` scaffold with workspace shell, tokenized styles, base UI primitives, static preview routes, and shell smoke tests.
- 2026-03-24: Added env/runtime config parsing, shared providers, API-client scaffolding, and reusable async-state primitives to the frontend foundation.
- 2026-03-24: Installed frontend dependencies, fixed lint/test runner issues, passed `make check`, and moved Story 7.1 to `done`.
