# Story 15.1: Add STT Provider Adapter Layer

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a backend team,
I want speech-to-text providers isolated behind adapters,
so that transcription can run in production without coupling business logic to a single vendor.

## Acceptance Criteria

1. Given transcription is required for a job, when STT execution runs, then business logic calls a provider adapter rather than provider SDK code directly.
2. Given multiple STT backends are supported, when configuration changes, then the selected provider can switch without changing domain logic.
3. Given provider output is returned, when it enters the application, then it is normalized into internal transcript models and error semantics.

## Tasks / Subtasks

- [ ] Add `adapters/stt/` interfaces and provider implementations for the selected production strategy.
- [ ] Normalize provider responses and failure modes into internal models.
- [ ] Wire STT selection through runtime configuration.
- [ ] Add tests for provider selection, normalized output, and error handling.
- [ ] Document operational requirements such as credentials, timeouts, and model settings.

## Dev Notes

### Developer Context Section

- The repository currently has no STT adapter layer even though the environment template describes STT provider settings.
- This story should keep provider calls out of business logic and preserve future portability.
- It depends on the configuration contract and workflow runtime being in place.

### Technical Requirements

- Business logic must not call provider SDKs directly.
- Adapter outputs must normalize transcript content and metadata to internal schemas.
- Sensitive inputs and outputs must not leak into logs.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/adapters/stt/`
- `apps/api/app/services/`
- `apps/api/tests/`
- runtime config docs if needed

### Testing Requirements

- Verify provider selection is configuration-driven.
- Verify normalized transcript output matches internal expectations.
- Verify provider failures map to safe internal errors.

### References

- `AGENTS.md`
- `.env.example`
- `apps/api/app/adapters/`
- `_bmad-output/planning-artifacts/architecture.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `AGENTS.md`
- `.env.example`
- `apps/api/app/adapters/`

### Completion Notes List

- 2026-04-05: Created Story 15.1 artifact for the STT provider adapter layer.

### File List

- `_bmad-output/implementation-artifacts/15-1-add-stt-provider-adapter-layer.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 15.1 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
