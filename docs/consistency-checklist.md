# Consistency Checklist (v1)

Use this checklist before merging planning/spec documentation updates.

## Authoritative Sources

1. API contract: `spec/api/openapi.yaml`
2. Job lifecycle rules: `spec/domain/job_fsm.md`
3. Agent safety and process rules: `AGENTS.md`

## Required Invariants

1. Product name is `Howera` in all project-facing docs.
2. `DRAFT_READY` means LLM draft is generated and stored.
3. `DONE` means at least one export succeeded and is retrievable.
4. Export status FSM is `REQUESTED -> RUNNING -> SUCCEEDED|FAILED`.
5. Callback semantics are:
   - first accepted event: `204`
   - identical replay: `200` with replay marker and no mutation
   - same event id with different payload: `409 EVENT_ID_PAYLOAD_MISMATCH`
6. v1 access model: one `editor` role; each user sees only own projects; project sharing is out of scope.
7. No-existence-leak policy is consistent where defined by contract (`404 RESOURCE_NOT_FOUND` for missing or unauthorized resource).
8. Screenshot lifecycle is in v1 scope: extract, poll task, create/list/get anchors, replace, soft-delete, upload/confirm, attach-upload, annotations.
9. `POST /jobs/{jobId}/confirm-upload` expects `200` on success/replay by contract.
10. `/healthz` is operational and intentionally outside OpenAPI contract checks.

## Quick Regression Checks

Run from repo root:

```bash
rg -n "Video2Inst|video2inst" AGENTS.md CONTRIBUTING.md docs spec _bmad-output
rg -n "200 or 204|204 or 200" docs spec _bmad-output
rg -n "Project sharing|sharing projects|collaboration across users" _bmad-output/planning-artifacts
```
