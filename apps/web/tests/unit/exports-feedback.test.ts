import assert from "node:assert/strict";
import test from "node:test";

import { ApiClientError } from "../../src/shared/api/errors";
import {
  createExportIdempotencyKey,
  describeExportError,
  describeExportPolling,
  describeExportRecord,
  getExportDownloadAvailability,
  getExportStatusTone,
} from "../../src/features/exports/feedback";

test("export feedback helpers cover replay, terminal states, and polling copy", () => {
  assert.match(createExportIdempotencyKey(), /^export-/);
  assert.equal(getExportStatusTone("REQUESTED"), "info");
  assert.equal(getExportStatusTone("RUNNING"), "warning");
  assert.equal(getExportStatusTone("SUCCEEDED"), "success");
  assert.equal(getExportStatusTone("FAILED"), "danger");

  assert.deepEqual(
    describeExportRecord({
      created_at: "2026-03-27T10:00:00Z",
      format: "PDF",
      id: "export-123",
      identity_key: "identity-123",
      instruction_version_id: "7",
      job_id: "job-123",
      replayed: true,
      screenshot_set_hash: "hash-123",
      status: "SUCCEEDED",
      updated_at: "2026-03-27T10:05:00Z",
    }),
    {
      description:
        "An earlier PDF export request already produced export export-123. This existing record remains the active result for instruction version 7.",
      title: "Existing export already ready",
      tone: "success",
    },
  );

  assert.deepEqual(
    describeExportRecord({
      created_at: "2026-03-27T10:00:00Z",
      format: "MD_ZIP",
      id: "export-456",
      identity_key: "identity-456",
      instruction_version_id: "7",
      job_id: "job-123",
      screenshot_set_hash: "hash-456",
      status: "FAILED",
      updated_at: "2026-03-27T10:05:00Z",
    }),
    {
      description:
        "Export export-456 reached FAILED for instruction version 7. Request the format again from the current workspace if you need to re-check or replay this export identity.",
      title: "Export failed",
      tone: "danger",
    },
  );

  assert.equal(
    describeExportPolling(
      {
        active: true,
        attemptsRemaining: 6,
        intervalMs: 2500,
        lastPolledAt: null,
        maxAttempts: 10,
        reason: "export-status",
        startedAt: "2026-03-27T10:00:00Z",
        watchValue: "export-123,export-456",
      },
      2,
    ),
    "Tracking 2 in-flight exports with bounded polling. 6 of 10 attempts remaining.",
  );
});

test("export error feedback preserves no-leak and validation-safe messaging", () => {
  assert.deepEqual(
    describeExportError(
      new ApiClientError(404, {
        code: "RESOURCE_NOT_FOUND",
        message: "Resource not found",
      }),
      "request",
    ),
    {
      description:
        "The export context is either missing or no longer accessible to this editor. Howera intentionally uses the same response for both cases.",
      title: "Export context unavailable",
      tone: "danger",
    },
  );

  assert.deepEqual(
    describeExportError(
      new ApiClientError(400, {
        code: "EXPORT_REQUEST_INVALID",
        message: "Unsupported format or invalid instruction version.",
      }),
      "request",
    ),
    {
      description: "Unsupported format or invalid instruction version.",
      title: "Export request rejected",
      tone: "warning",
    },
  );
});

test("export download availability covers pending, failed, missing, expired, and ready states", () => {
  assert.deepEqual(
    getExportDownloadAvailability(
      {
        created_at: "2026-03-27T10:00:00Z",
        format: "PDF",
        id: "export-pending-123",
        identity_key: "identity-pending-123",
        instruction_version_id: "7",
        job_id: "job-123",
        screenshot_set_hash: "hash-pending-123",
        status: "RUNNING",
        updated_at: "2026-03-27T10:05:00Z",
      },
      Date.parse("2026-03-27T10:06:00Z"),
    ),
    {
      canDownload: false,
      description:
        "Download becomes available after this export reaches SUCCEEDED. Keep polling or refresh status to fetch a signed URL when processing finishes.",
      state: "pending",
      title: "Download not ready",
      tone: "warning",
    },
  );

  assert.deepEqual(
    getExportDownloadAvailability(
      {
        created_at: "2026-03-27T10:00:00Z",
        format: "MD_ZIP",
        id: "export-failed-123",
        identity_key: "identity-failed-123",
        instruction_version_id: "7",
        job_id: "job-123",
        screenshot_set_hash: "hash-failed-123",
        status: "FAILED",
        updated_at: "2026-03-27T10:05:00Z",
      },
      Date.parse("2026-03-27T10:06:00Z"),
    ),
    {
      canDownload: false,
      description:
        "Download unavailable because this export failed. Request the format again or refresh status after a retry to restore a usable result.",
      state: "failed",
      title: "Download unavailable",
      tone: "danger",
    },
  );

  assert.deepEqual(
    getExportDownloadAvailability(
      {
        created_at: "2026-03-27T10:00:00Z",
        format: "PDF",
        id: "export-missing-123",
        identity_key: "identity-missing-123",
        instruction_version_id: "7",
        job_id: "job-123",
        screenshot_set_hash: "hash-missing-123",
        status: "SUCCEEDED",
        updated_at: "2026-03-27T10:05:00Z",
      },
      Date.parse("2026-03-27T10:06:00Z"),
    ),
    {
      canDownload: false,
      description:
        "Signed download URL is not loaded yet. Download or refresh status to request a current scoped URL for this completed export.",
      state: "missing-url",
      title: "Signed URL unavailable",
      tone: "warning",
    },
  );

  assert.deepEqual(
    getExportDownloadAvailability(
      {
        created_at: "2026-03-27T10:00:00Z",
        download_url: "https://downloads.howera.local/export-expired-123?sig=abc",
        download_url_expires_at: "2026-03-27T10:04:00Z",
        format: "PDF",
        id: "export-expired-123",
        identity_key: "identity-expired-123",
        instruction_version_id: "7",
        job_id: "job-123",
        screenshot_set_hash: "hash-expired-123",
        status: "SUCCEEDED",
        updated_at: "2026-03-27T10:05:00Z",
      },
      Date.parse("2026-03-27T10:06:00Z"),
    ),
    {
      canDownload: false,
      description:
        "The signed download URL expired at Mar 27, 2026, 10:04 AM UTC. Download again or refresh status to request a new scoped URL.",
      state: "expired",
      title: "Signed URL expired",
      tone: "warning",
    },
  );

  assert.deepEqual(
    getExportDownloadAvailability(
      {
        created_at: "2026-03-27T10:00:00Z",
        download_url: "https://downloads.howera.local/export-ready-123?sig=abc",
        download_url_expires_at: "2026-03-27T10:20:00Z",
        format: "PDF",
        id: "export-ready-123",
        identity_key: "identity-ready-123",
        instruction_version_id: "7",
        job_id: "job-123",
        screenshot_set_hash: "hash-ready-123",
        status: "SUCCEEDED",
        updated_at: "2026-03-27T10:05:00Z",
      },
      Date.parse("2026-03-27T10:06:00Z"),
    ),
    {
      canDownload: true,
      description:
        "Signed URL ready until Mar 27, 2026, 10:20 AM UTC. It is used immediately from in-memory state and is never persisted in browser storage.",
      state: "ready",
      title: "Download ready",
      tone: "success",
    },
  );
});
