# Story 16.1: Harden HTTP Edge Policy and Runtime Security Defaults

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a platform team,
I want secure HTTP and edge defaults,
so that the deployed application is not relying on permissive local-development behavior in production.

## Acceptance Criteria

1. Given the API is deployed behind its intended edge, when requests arrive, then host validation, HTTPS assumptions, CORS, and request-size policy are explicitly defined.
2. Given abusive or malformed traffic reaches the service, when runtime security policy is applied, then rate or shape controls reduce risk without breaking the public contract.
3. Given secure defaults are configured, when operators review the stack, then auth, callback, and download surfaces are not exposed by overly permissive middleware settings.

## Tasks / Subtasks

- [ ] Define production HTTP and edge security policy for API and web entry points.
- [ ] Implement or document the required middleware and reverse-proxy controls.
- [ ] Add request-size, trusted-host, HTTPS, and CORS protections aligned with the chosen deployment topology.
- [ ] Add rate-limiting or equivalent abuse controls for critical write surfaces.
- [ ] Add tests or configuration verification for the enforced policy.

## Dev Notes

### Developer Context Section

- The current FastAPI app does not show explicit CORS, trusted-host, or HTTPS middleware registration.
- This story should make production security defaults visible and reviewable rather than implicit.
- It should stay aligned with deployment decisions from the production architecture stories.

### Technical Requirements

- Preserve authenticated write requirements from `AGENTS.md`.
- Keep callback and download flows functional under stricter edge policy.
- Avoid exposing development-only origins or hosts in production defaults.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/main.py`
- deployment or ingress configuration
- security-related docs
- `apps/api/tests/`

### Testing Requirements

- Verify policy behavior for allowed and disallowed origins or hosts.
- Verify secure defaults do not break legitimate authenticated workflows.
- Verify request-size or abuse protections are enforced as intended.

### References

- `AGENTS.md`
- `apps/api/app/main.py`
- `_bmad-output/planning-artifacts/architecture.md`
- `.env.example`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `AGENTS.md`
- `apps/api/app/main.py`
- `_bmad-output/planning-artifacts/architecture.md`

### Completion Notes List

- 2026-04-05: Created Story 16.1 artifact for HTTP edge policy and secure runtime defaults.

### File List

- `_bmad-output/implementation-artifacts/16-1-harden-http-edge-policy-and-runtime-security-defaults.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 16.1 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
