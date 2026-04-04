import assert from "node:assert/strict";
import test from "node:test";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { WorkspaceShellFrame } from "../../src/features/shell/components/workspace-shell-frame";
import { Button } from "../../src/shared/ui/button";

test("workspace shell renders navigation, content, and context regions", () => {
  const html = renderToStaticMarkup(
    <WorkspaceShellFrame pathname="/projects">
      <section>
        <h2>Workspace body</h2>
      </section>
    </WorkspaceShellFrame>,
  );

  assert.match(html, /Skip to workspace content/);
  assert.match(html, /href="#workspace-content"/);
  assert.match(html, /aria-label="Primary workspace navigation"/);
  assert.match(html, /aria-label="Workspace content"/);
  assert.match(html, /id="workspace-content"/);
  assert.match(html, /tabindex="-1"/);
  assert.match(html, /Shared shell contract/);
  assert.match(html, /Workspace body/);
  assert.match(html, /firebase-hosting for the development environment/);
  assert.match(html, /Safe telemetry hooks are wired, but emission is disabled for this environment/);
});

test("workspace shell shows deployment and telemetry posture from runtime config", () => {
  const html = renderToStaticMarkup(
    <WorkspaceShellFrame
      appEnv="staging"
      foundationQueryVersion={2}
      hasApiClient
      hostingTarget="firebase-preview"
      pathname="/jobs"
      telemetryEnabled
    >
      <section>
        <h2>Job detail</h2>
      </section>
    </WorkspaceShellFrame>,
  );

  assert.match(html, /firebase-preview for the staging environment/);
  assert.match(html, /Safe telemetry emission is enabled with sanitized browser events/);
  assert.match(html, /Foundation query revision: 2/);
  assert.match(html, /Shared client provider is mounted for workspace routes/);
});

test("button primitive defaults to a safe button type", () => {
  const html = renderToStaticMarkup(<Button>Run workflow</Button>);

  assert.match(html, /type="button"/);
  assert.match(html, /focus-ring/);
});
