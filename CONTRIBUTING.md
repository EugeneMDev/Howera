# Contributing Guide — Howera

This repository is developed using **Spec-Driven Development** and **agentic workflows** (Codex).
The goal is deterministic, testable increments.

---

## 1. Golden Rules

1. `spec/` is source of truth.
   Do not change specs in feature PRs unless explicitly requested.
2. Small diffs only.
   One task = one logical change.
3. Route handlers must remain thin.
   Business logic in domain/services.
4. External calls must go through adapters.
   No direct OpenAI/Firebase calls inside routes.
5. Always end work with `make check`.

---

## 2. Branching & PRs

### Branch naming

- `feat/<short-name>`
- `fix/<short-name>`
- `chore/<short-name>`

### PR requirements

- Link to task/spec section (e.g., `spec/acceptance/tasks_codex_v1.md#TASK-06`)
- Include:
  - Summary
  - Modified files list
  - How to test (commands + expected output)

---

## 3. Code Organization (Backend)

Recommended structure:

- `app/routes/` — HTTP layer (thin)
- `app/domain/` — FSM, entities, invariants
- `app/services/` — orchestration/business logic
- `app/adapters/` — OpenAI, Firebase, MinIO, STT providers
- `app/repos/` — persistence abstraction + implementations
- `app/schemas/` — pydantic models for API

No direct persistence in services without repo interface.

---

## 4. Testing Policy

### Required on every PR

- Unit tests for domain logic (FSM)
- Contract smoke tests for OpenAPI paths existence
- Golden Path mock-mode e2e must pass

### Optional / gated

- Integration tests requiring real Firebase/OpenAI:
  - run locally only unless CI configured

---

## 5. Formatting & Lint

Backend must pass:

- Ruff (lint)
- Black (format)
- mypy (type checks)
- pytest (tests)

Run:

```bash
make check
```

## 6. Spec Change Process

If you need to modify specs:

- Create a dedicated PR:
- Update spec document(s)
- Add/update ADR if decision changes

- Only after spec is merged, implement code changes.

## 7. Agent (Codex) Workflow Rules

When using Codex:

- Provide a Task Card with:
  - Goal / Non-goals
  - Allowed paths
  - Acceptance checks

- Reject large refactors not requested.

- Require final output:
  - make check results
  - summary + modified files

## 8. Security Requirements

Never commit secrets:

- `.env`
- API keys
- service account keys

Use .env.example + secret manager for real values.

Any internal callback must be authenticated (secret + idempotency header).

## 9. Commit Message Convention

- `feat: ...`
- `fix: ...`
- `chore: ...`
- `docs: ...`
- `test: ...`

Example:

`feat: enforce job FSM transitions`
