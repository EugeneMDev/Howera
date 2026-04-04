import assert from "node:assert/strict";
import test from "node:test";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { JobLifecycleTimeline } from "../../src/features/jobs/components/job-lifecycle-timeline";
import {
  createClientRequestId,
  getJobLifecycleActionDisabledState,
  getJobLifecycleActionAvailability,
  getLifecycleTimelineState,
} from "../../src/features/jobs/lifecycle";

test("job lifecycle availability only exposes contract-safe actions", () => {
  assert.deepEqual(getJobLifecycleActionAvailability({ status: "CREATED" }), {
    canCancel: true,
    canConfirmUpload: true,
    canRetry: false,
    canRun: false,
  });
  assert.deepEqual(getJobLifecycleActionAvailability({ status: "UPLOADED" }), {
    canCancel: true,
    canConfirmUpload: false,
    canRetry: false,
    canRun: true,
  });
  assert.deepEqual(getJobLifecycleActionAvailability({ status: "FAILED" }), {
    canCancel: false,
    canConfirmUpload: false,
    canRetry: true,
    canRun: false,
  });
  assert.deepEqual(getJobLifecycleActionAvailability({ status: "DONE" }), {
    canCancel: false,
    canConfirmUpload: false,
    canRetry: false,
    canRun: false,
  });
});

test("job lifecycle timeline states stay conservative for terminal statuses", () => {
  assert.equal(getLifecycleTimelineState("CREATED", "UPLOADED"), "completed");
  assert.equal(getLifecycleTimelineState("UPLOADED", "UPLOADED"), "current");
  assert.equal(getLifecycleTimelineState("AUDIO_EXTRACTING", "UPLOADED"), "pending");
  assert.equal(getLifecycleTimelineState("CREATED", "FAILED"), "completed");
  assert.equal(getLifecycleTimelineState("UPLOADED", "FAILED"), "pending");
});

test("job lifecycle disables conflicting controls while a lifecycle mutation is in flight", () => {
  const availability = {
    canCancel: true,
    canConfirmUpload: true,
    canRetry: false,
    canRun: true,
  };

  assert.deepEqual(getJobLifecycleActionDisabledState(availability, null), {
    cancelDisabled: false,
    confirmUploadDisabled: false,
    inputDisabled: false,
    retryDisabled: true,
    runDisabled: false,
  });

  assert.deepEqual(getJobLifecycleActionDisabledState(availability, "run"), {
    cancelDisabled: true,
    confirmUploadDisabled: true,
    inputDisabled: true,
    retryDisabled: true,
    runDisabled: true,
  });
});

test("job lifecycle timeline renders current and terminal status messaging", () => {
  const activeHtml = renderToStaticMarkup(
    <JobLifecycleTimeline
      job={{
        created_at: "2026-03-24T10:00:00Z",
        id: "job-123",
        project_id: "project-123",
        status: "DRAFT_READY",
        updated_at: "2026-03-24T10:05:00Z",
      }}
    />,
  );
  const terminalHtml = renderToStaticMarkup(
    <JobLifecycleTimeline
      job={{
        created_at: "2026-03-24T10:00:00Z",
        id: "job-456",
        project_id: "project-123",
        status: "FAILED",
        updated_at: "2026-03-24T10:06:00Z",
      }}
    />,
  );

  assert.match(activeHtml, /DRAFT_READY/);
  assert.match(activeHtml, /Current status updated/);
  assert.match(terminalHtml, /FAILED/);
  assert.match(terminalHtml, /Terminal status recorded/);
});

test("retry client request ids are prefixed for lifecycle actions", () => {
  assert.match(createClientRequestId(), /^retry-/);
  assert.match(createClientRequestId("custom"), /^custom-/);
});
