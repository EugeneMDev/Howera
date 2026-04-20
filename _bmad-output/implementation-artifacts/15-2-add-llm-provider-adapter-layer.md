# Story 15.2: Add LLM Provider Adapter Layer

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a backend team,
I want LLM access isolated behind adapters,
so that draft generation and regenerate flows can evolve without coupling domain logic to one provider SDK.

## Acceptance Criteria

1. Given instruction generation or regenerate work is executed, when the system calls an LLM, then it does so through an adapter boundary rather than direct SDK usage in business logic.
2. Given multiple model backends or profiles are supported, when configuration changes, then model selection and timeout behavior remain externalized.
3. Given provider responses or failures occur, when the application handles them, then outputs and errors are normalized to internal models and safe messages.

## Tasks / Subtasks

- [ ] Add `adapters/llm/` interfaces and provider implementations for the selected production strategy.
- [ ] Normalize generated content, metadata, and error semantics into internal models.
- [ ] Wire model profile and provider selection through runtime configuration.
- [ ] Update regenerate or generation services to consume the adapter layer exclusively.
- [ ] Add tests for provider switching, normalized output, and safe error handling.

## Dev Notes

### Developer Context Section

- The repository currently lacks an LLM adapter layer even though the product architecture expects provider isolation.
- This story should support both current and future model-profile policies without leaking provider details into core services.
- It depends on the configuration contract and workflow path being production-capable first.

### Technical Requirements

- Business logic must never call the LLM provider directly.
- Keep prompt and model selection policy externalized from domain flows.
- Do not log raw prompt context or secrets.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/adapters/llm/`
- `apps/api/app/services/`
- `apps/api/tests/`
- runtime config docs if needed

### Testing Requirements

- Verify model or provider selection is configuration-driven.
- Verify normalized outputs fit internal instruction-generation needs.
- Verify provider failures map to safe, contract-compatible errors.

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

- 2026-04-05: Created Story 15.2 artifact for the LLM provider adapter layer.

### File List

- `_bmad-output/implementation-artifacts/15-2-add-llm-provider-adapter-layer.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 15.2 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
