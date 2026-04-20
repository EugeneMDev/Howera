import assert from "node:assert/strict";
import test from "node:test";

import { formatDateTime } from "../../src/shared/lib/format-date";

test("formatDateTime uses a deterministic UTC representation", () => {
  const formatted = formatDateTime("2026-03-24T10:00:00Z");

  assert.match(formatted, /2026/);
  assert.match(formatted, /UTC$/);
});
