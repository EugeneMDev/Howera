import assert from "node:assert/strict";
import test from "node:test";

import { buildSignInPath, normalizeNextPath } from "../../src/features/auth/redirect";

test("normalizeNextPath keeps safe internal workspace paths", () => {
  assert.equal(normalizeNextPath("/projects/123"), "/projects/123");
  assert.equal(normalizeNextPath("/jobs?status=queued"), "/jobs?status=queued");
});

test("normalizeNextPath falls back for unsafe or auth-loop paths", () => {
  assert.equal(normalizeNextPath(undefined), "/projects");
  assert.equal(normalizeNextPath(null), "/projects");
  assert.equal(normalizeNextPath("https://example.com"), "/projects");
  assert.equal(normalizeNextPath("//evil.example"), "/projects");
  assert.equal(normalizeNextPath("/sign-in"), "/projects");
  assert.equal(normalizeNextPath("/sign-in?next=%2Fjobs"), "/projects");
});

test("buildSignInPath normalizes and encodes next paths", () => {
  assert.equal(buildSignInPath("/projects/123"), "/sign-in?next=%2Fprojects%2F123");
  assert.equal(buildSignInPath("https://example.com"), "/sign-in?next=%2Fprojects");
});
