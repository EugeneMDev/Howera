# Story 12.2: Align Runtime Config Contract and Environment Documentation

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a platform operator,
I want one authoritative runtime configuration contract,
so that local, staging, and production environments are deterministic and do not drift from the code.

## Acceptance Criteria

1. Given backend and frontend runtimes require environment configuration, when the config contract is finalized, then env names, prefixes, defaults, and required variables are consistent across code and documentation.
2. Given a required production variable is missing or malformed, when the service starts, then startup fails clearly instead of silently falling back to unsafe defaults.
3. Given developers provision environments, when they use the example env files and docs, then the documented variables match what the application actually reads.

## Tasks / Subtasks

- [ ] Inventory current env drift across backend settings, docs, and examples.
- [ ] Define the canonical production env contract and naming scheme.
- [ ] Update backend and frontend config loaders to validate required variables explicitly.
- [ ] Update `.env` examples and setup documentation to match the runtime contract exactly.
- [ ] Add tests for required-variable validation and mode-specific defaults.

## Dev Notes

### Developer Context Section

- The current backend settings surface is much smaller than the documented env template, so this story should remove ambiguity before infrastructure work.
- Frontend runtime config already expects `NEXT_PUBLIC_*` values and should stay aligned with deployment documentation.
- This story unblocks API runtime packaging, persistence, providers, and deploy automation.

### Technical Requirements

- Keep configuration environment-driven for both API and web runtimes.
- Avoid hidden defaults for production-only secrets or external dependency endpoints.
- Distinguish mock or local-development settings from production settings explicitly.
- Maintain backward clarity for developers migrating from the current scaffold.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/core/`
- `apps/web/src/shared/config/`
- `.env.example`
- `env.md`
- `docs/dev-setup.md`

### Testing Requirements

- Verify required settings are validated at startup.
- Verify example env documentation matches the loaded runtime keys.
- Verify mock and production modes are selected explicitly, not implicitly.

### References

- `.env.example`
- `env.md`
- `docs/dev-setup.md`
- `apps/api/app/core/config.py`
- `apps/web/src/shared/config/runtime.ts`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `.env.example`
- `env.md`
- `docs/dev-setup.md`
- `apps/api/app/core/config.py`

### Completion Notes List

- 2026-04-05: Created Story 12.2 artifact for the unified runtime-config and environment-documentation contract.

### File List

- `_bmad-output/implementation-artifacts/12-2-align-runtime-config-contract-and-environment-documentation.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 12.2 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
