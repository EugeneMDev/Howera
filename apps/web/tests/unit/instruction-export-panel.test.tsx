import assert from "node:assert/strict";
import test from "node:test";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { InstructionExportPanel } from "../../src/features/exports/components/instruction-export-panel";

test("export panel renders request controls, polling metadata, and export record states", () => {
  const html = renderToStaticMarkup(
    <InstructionExportPanel
      currentInstructionVersion={7}
      exportsState={{
        dismissFeedback() {},
        feedback: {
          description:
            "An earlier MD_ZIP export request already created export export-md-123. Tracking continues from its current requested state without duplicating workspace history.",
          title: "Existing export restored",
          tone: "info",
        },
        isSubmitting: false,
        lastIdempotencyKey: "export-md-123",
        pendingDownloadExportId: null,
        polling: {
          active: true,
          attemptsRemaining: 6,
          intervalMs: 2500,
          lastPolledAt: "2026-03-27T10:08:00Z",
          maxAttempts: 10,
          reason: "export-status",
          startedAt: "2026-03-27T10:07:00Z",
          watchValue: "export-md-123,export-pdf-123",
        },
        records: [
          {
            created_at: "2026-03-27T10:05:00Z",
            format: "MD_ZIP",
            id: "export-md-123",
            identity_key: "identity-md-123",
            instruction_version_id: "7",
            job_id: "job-123",
            replayed: true,
            screenshot_set_hash: "hash-md-123",
            status: "REQUESTED",
            updated_at: "2026-03-27T10:08:00Z",
          },
          {
            created_at: "2026-03-27T10:00:00Z",
            format: "PDF",
            id: "export-pdf-123",
            identity_key: "identity-pdf-123",
            instruction_version_id: "7",
            job_id: "job-123",
            last_audit_event: "EXPORT_FAILED",
            screenshot_set_hash: "hash-pdf-123",
            status: "FAILED",
            updated_at: "2026-03-27T10:06:00Z",
          },
        ],
        async downloadExport() {
          return true;
        },
        async refreshExport() {},
        async submit() {
          return true;
        },
        stopPolling() {},
      }}
      isDirty={true}
      jobId="job-123"
    />,
  );

  assert.match(html, /Request deliverables and track export state/);
  assert.match(html, /Unsaved draft edits are not included in export requests/);
  assert.match(html, /Request MD_ZIP/);
  assert.match(html, /Request PDF/);
  assert.match(html, /Tracking 1 in-flight export with bounded polling/);
  assert.match(html, /Last idempotency key: export-md-123/);
  assert.match(html, /Export records/);
  assert.match(html, /Replay/);
  assert.match(html, /Request again/);
  assert.match(
    html,
    /Download becomes available after this export reaches SUCCEEDED\. Keep polling or refresh status to fetch a signed URL when processing finishes\./,
  );
  assert.match(
    html,
    /Download unavailable because this export failed\. Request the format again or refresh status after a retry to restore a usable result\./,
  );
  assert.equal(
    html.match(/<button[^>]*aria-describedby=\"export-download-guidance-[^\"]+\"[^>]*disabled=\"\"[^>]*>Download export<\/button>/g)
      ?.length,
    2,
  );
  assert.match(html, /identity-pdf-123/);
});
