# Story 11.4: Prepare Deployment Config and Safe Telemetry

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a platform team,
I want deployment configuration and telemetry prepared safely,
so that frontend rollout is controlled and observability remains non-sensitive.

## Acceptance Criteria

1. Given a release candidate is built, when deployment configuration is validated, then API base URL and Firebase runtime settings are environment-driven and the app is deployable to the chosen hosting target.
2. Given telemetry is emitted for key UI actions, when events are recorded, then they correlate to job, task, and export identifiers and logs exclude tokens, raw transcript content, and signed URLs.

## Tasks / Subtasks

- [x] Add environment-driven frontend config for API base URL and Firebase runtime values.
- [x] Prepare deployment configuration for the selected hosting target.
- [x] Add safe telemetry interface for key UI actions and async workflow milestones.
- [x] Correlate telemetry to non-sensitive identifiers such as job, task, and export IDs.
- [x] Exclude bearer tokens, transcript bodies, and signed URLs from telemetry and logs.
- [x] Add tests or verification checks for config loading and telemetry redaction rules.

## Dev Notes

### Developer Context Section

- Architecture selects Firebase Hosting and environment-driven runtime config for frontend deployment.
- Telemetry is optional infrastructure-wise but must stay non-sensitive from day one.
- This story should finalize rollout-readiness after the core flows and quality gates exist.

### Technical Requirements

- Keep API base URL and Firebase settings outside hardcoded source values.
- Ensure the app can be deployed with environment-specific configuration.
- Use a shared telemetry interface rather than ad hoc `console.log` style instrumentation.
- Never emit tokens, raw transcript content, or signed URLs.

### File Structure Requirements

- Primary expected touch points:
- `apps/web/src/shared/lib/`
- `apps/web/src/shared/api/`
- deployment config files under frontend or infra scope
- `apps/web/tests/`

### Testing Requirements

- Verify environment config resolution for multiple environments.
- Verify telemetry events include only safe identifiers and metadata.
- Verify sensitive values are redacted or omitted entirely.
- Verify deployment configuration is compatible with the selected hosting target.

### References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `AGENTS.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `AGENTS.md`

### Completion Notes List

- 2026-03-24: Created Story 11.4 artifact with deployment-config and safe-telemetry scope.
- 2026-03-24: Captured environment-driven config and sensitive-data exclusion requirements for frontend implementation.
- 2026-04-04: Extended frontend public runtime config with deployment labels and a telemetry feature flag, and removed the hardcoded API base URL fallback so deployment configuration must come from `NEXT_PUBLIC_*` env values.
- 2026-04-04: Added a shared safe telemetry client with allowlisted attributes plus redaction for bearer tokens, signed URLs, multiline content, and other unsafe strings; wired it into project creation, job lifecycle, instruction save/regenerate, screenshot extraction, and export flows.
- 2026-04-04: Added Firebase Hosting config at the repo root and documented the frontend public runtime variables in `apps/web/.env.example`, `env.md`, and `docs/dev-setup.md`.
- 2026-04-04: Verified deployment/runtime loading and telemetry redaction with targeted unit tests, then passed `make lint`, `make test`, and `make check` in `apps/web`.

### File List

- `_bmad-output/implementation-artifacts/11-4-prepare-deployment-config-and-safe-telemetry.md`
- `firebase.json`
- `env.md`
- `docs/dev-setup.md`
- `apps/web/.env.example`
- `apps/web/src/shared/api/client.ts`
- `apps/web/src/shared/config/runtime.ts`
- `apps/web/src/shared/lib/telemetry.ts`
- `apps/web/src/shared/providers/app-providers.tsx`
- `apps/web/src/features/projects/hooks.ts`
- `apps/web/src/features/jobs/hooks.ts`
- `apps/web/src/features/instructions/hooks.ts`
- `apps/web/src/features/instructions/regenerate-hooks.ts`
- `apps/web/src/features/screenshots/hooks.ts`
- `apps/web/src/features/exports/hooks.ts`
- `apps/web/src/features/shell/components/workspace-shell.tsx`
- `apps/web/src/features/shell/components/workspace-shell-frame.tsx`
- `apps/web/tests/unit/api-client.test.ts`
- `apps/web/tests/unit/runtime-config.test.ts`
- `apps/web/tests/unit/telemetry.test.ts`
- `apps/web/tests/unit/deployment-config.test.ts`
- `apps/web/tests/unit/workspace-shell.test.tsx`
- `_bmad-output/implementation-artifacts/frontend-sprint-status.yaml`

### Change Log

- 2026-03-24: Created Story 11.4 artifact and moved frontend story status from `backlog` to `ready-for-dev`.
- 2026-04-04: Completed Story 11.4 with environment-driven deployment config, safe telemetry instrumentation, hosting/runtime documentation, and verification coverage.
