import assert from "node:assert/strict";
import test from "node:test";

import { ApiClientError } from "../../src/shared/api/errors";
import {
  createTelemetryClient,
  sanitizeTelemetryAttributes,
  sanitizeTelemetryEvent,
} from "../../src/shared/lib/telemetry";

test("telemetry sanitization preserves allowlisted identifiers and omits unapproved fields", () => {
  const attributes = sanitizeTelemetryAttributes({
    action: "export",
    anchorId: "anchor-123",
    appEnv: "production",
    authHeader: "Bearer secret-token",
    downloadUrl: "https://signed.example/download?sig=secret",
    exportId: "export-456",
    format: "PDF",
    httpStatus: 200,
    instructionId: "instruction-789",
    jobId: "job-123",
    reason: "https://signed.example/download?sig=secret",
    result: "succeeded",
    status: "SUCCEEDED",
    taskId: "task-321",
    transcriptText: "speaker one said hello",
    uploadId: "upload-654",
    versionConflict: "4->5",
  });

  assert.deepEqual(attributes, {
    action: "export",
    anchorId: "anchor-123",
    appEnv: "production",
    exportId: "export-456",
    format: "PDF",
    httpStatus: 200,
    instructionId: "instruction-789",
    jobId: "job-123",
    reason: "[redacted]",
    result: "succeeded",
    status: "SUCCEEDED",
    taskId: "task-321",
    uploadId: "upload-654",
    versionConflict: "4->5",
  });
});

test("telemetry event sanitization adds safe defaults and error metadata without leaking messages", () => {
  const record = sanitizeTelemetryEvent(
    {
      attributes: {
        exportId: "export-456",
        jobId: "job-123",
        reason: "line one\nline two",
        result: "failed",
        status: "FAILED",
      },
      error: new ApiClientError(403, {
        code: "SIGNED_URL_REJECTED",
        message: "signed url https://signed.example/download?sig=secret",
      }),
      name: "export.download.failed",
    },
    {
      appEnv: "staging",
      authProvider: "firebase",
      hostingTarget: "firebase-hosting",
    },
  );

  assert.equal(record.name, "export.download.failed");
  assert.equal(record.attributes.appEnv, "staging");
  assert.equal(record.attributes.authProvider, "firebase");
  assert.equal(record.attributes.hostingTarget, "firebase-hosting");
  assert.equal(record.attributes.exportId, "export-456");
  assert.equal(record.attributes.jobId, "job-123");
  assert.equal(record.attributes.reason, "[redacted]");
  assert.equal(record.attributes.result, "failed");
  assert.equal(record.attributes.status, "FAILED");
  assert.equal(record.attributes.errorCode, "SIGNED_URL_REJECTED");
  assert.equal(record.attributes.httpStatus, 403);
  assert.ok(Number.isFinite(Date.parse(record.occurredAt)));
  assert.ok(!("message" in record.attributes));
});

test("telemetry client emits only sanitized records when enabled", () => {
  const emitted: unknown[] = [];
  const disabledClient = createTelemetryClient({
    defaults: {
      appEnv: "development",
      authProvider: "mock",
      hostingTarget: "firebase-hosting",
    },
    emit: (record) => {
      emitted.push(record);
    },
    enabled: false,
  });

  disabledClient.track({
    attributes: {
      projectId: "project-123",
      result: "succeeded",
    },
    name: "project.create.succeeded",
  });

  assert.equal(emitted.length, 0);

  const enabledClient = createTelemetryClient({
    defaults: {
      appEnv: "development",
      authProvider: "mock",
      hostingTarget: "firebase-hosting",
    },
    emit: (record) => {
      emitted.push(record);
    },
    enabled: true,
  });

  enabledClient.track({
    attributes: {
      jobId: "job-456",
      reason: "Bearer secret-token",
      result: "failed",
    },
    error: new Error("NetworkError"),
    name: "instruction.save.failed",
  });

  assert.equal(emitted.length, 1);
  assert.deepEqual(emitted[0], {
    attributes: {
      appEnv: "development",
      authProvider: "mock",
      errorCode: "Error",
      hostingTarget: "firebase-hosting",
      jobId: "job-456",
      reason: "[redacted]",
      result: "failed",
    },
    name: "instruction.save.failed",
    occurredAt: (emitted[0] as { occurredAt: string }).occurredAt,
  });
  assert.ok(
    Number.isFinite(
      Date.parse((emitted[0] as { occurredAt: string }).occurredAt),
    ),
  );
});
