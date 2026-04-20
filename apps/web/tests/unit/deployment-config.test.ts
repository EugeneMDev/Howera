import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("firebase hosting config targets the frontend app source", () => {
  const rawConfig = readFileSync(new URL("../../../../firebase.json", import.meta.url), "utf8");
  const config = JSON.parse(rawConfig) as {
    hosting?: {
      ignore?: string[];
      source?: string;
    };
  };

  assert.equal(config.hosting?.source, "apps/web");
  assert.ok(config.hosting?.ignore?.includes("firebase.json"));
  assert.ok(config.hosting?.ignore?.includes("**/.*"));
  assert.ok(config.hosting?.ignore?.includes("**/node_modules/**"));
});
