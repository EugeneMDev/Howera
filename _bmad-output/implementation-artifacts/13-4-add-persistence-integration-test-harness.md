# Story 13.4: Add Persistence Integration Test Harness

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a delivery team,
I want a persistence-backed integration harness,
so that repository and callback behavior are verified against the real storage stack instead of only the scaffold.

## Acceptance Criteria

1. Given durable persistence and storage are introduced, when integration tests run, then they can exercise the real repository path against ephemeral test infrastructure.
2. Given core create, update, and callback flows are executed, when the harness runs, then failures identify repository or storage regressions rather than only unit-level scaffold issues.
3. Given CI adopts the new harness, when tests are executed repeatedly, then setup and teardown remain deterministic.

## Tasks / Subtasks

- [ ] Define the ephemeral integration environment required for the chosen persistence and storage stack.
- [ ] Add integration tests that cover project, job, instruction, callback, and artifact-manifest paths.
- [ ] Ensure the harness can isolate test data and clean up reliably between runs.
- [ ] Wire the harness into backend verification or CI-ready commands.
- [ ] Document how to run the persistence integration suite locally.

## Dev Notes

### Developer Context Section

- Existing tests validate business rules well, but much of the backend surface still assumes `InMemoryStore`.
- This story should provide the safety net needed before real workflow and provider integrations expand the stack.
- It depends on Stories 13.1 through 13.3 establishing the real persistence path.

### Technical Requirements

- Keep the integration harness deterministic and automation-friendly.
- Avoid requiring long-lived shared infrastructure for local or CI execution.
- Preserve existing unit-test speed by separating slower integration coverage appropriately.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/tests/`
- backend verification commands
- CI or local-stack bootstrap files if needed

### Testing Requirements

- Verify the integration harness covers durable repository and storage behavior.
- Verify test setup and teardown are repeatable across runs.
- Verify failures point to the broken persistence or storage stage clearly.

### References

- `apps/api/tests/`
- `apps/api/Makefile`
- `docs/dev-setup.md`
- `AGENTS.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `apps/api/tests/`
- `apps/api/Makefile`
- `docs/dev-setup.md`

### Completion Notes List

- 2026-04-05: Created Story 13.4 artifact for a persistence-backed integration test harness.

### File List

- `_bmad-output/implementation-artifacts/13-4-add-persistence-integration-test-harness.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 13.4 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
