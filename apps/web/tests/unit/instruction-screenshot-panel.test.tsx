import assert from "node:assert/strict";
import test from "node:test";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { InstructionScreenshotPanel } from "../../src/features/screenshots/components/instruction-screenshot-panel";

test("screenshot panel renders linkage, replay status, and polling freshness details", () => {
  const html = renderToStaticMarkup(
    <InstructionScreenshotPanel
      blockId=""
      contextMode="char_range"
      format="png"
      idempotencyKey="screenshot-123"
      isDirty={false}
      offsetMs="0"
      onBlockIdChange={() => {}}
      onContextModeChange={() => {}}
      onDismissFeedback={() => {}}
      onFormatChange={() => {}}
      onGenerateIdempotencyKey={() => {}}
      onIdempotencyKeyChange={() => {}}
      onOffsetMsChange={() => {}}
      onRefreshCurrentTask={() => {}}
      onStopPolling={() => {}}
      onStrategyChange={() => {}}
      onSubmit={() => {}}
      onTimestampMsChange={() => {}}
      screenshot={{
        dismissFeedback() {},
        feedback: {
          description: "Screenshot extraction completed and linked anchor anchor-123 to asset asset-456.",
          title: "Screenshot extracted",
          tone: "success",
        },
        isSubmitting: false,
        lastIdempotencyKey: "screenshot-123",
        polling: {
          active: false,
          attemptsRemaining: 0,
          intervalMs: 2500,
          lastPolledAt: "2026-03-25T10:05:00Z",
          maxAttempts: 10,
          reason: "screenshot-task-status",
          startedAt: "2026-03-25T10:00:00Z",
          watchValue: "screenshot-task-123",
        },
        refreshCurrentTask: async () => {},
        stopPolling() {},
        submit: async () => {},
        task: {
          anchor_id: "anchor-123",
          asset_id: "asset-456",
          operation: "extract",
          replayed: true,
          status: "SUCCEEDED",
          task_id: "screenshot-task-123",
        },
      }}
      selectedText="Selected instruction text"
      selection={{ direction: "forward", end: 24, start: 4 }}
      strategy="precise"
      timestampMs="12500"
    />,
  );

  assert.match(html, /Capture visual evidence/);
  assert.match(html, /Task screenshot-task-123/);
  assert.match(html, /Replay/);
  assert.match(html, /anchor-123/);
  assert.match(html, /asset-456/);
  assert.match(html, /<button[^>]*aria-pressed="true"[^>]*>precise<\/button>/);
  assert.match(html, /<button[^>]*aria-pressed="true"[^>]*>png<\/button>/);
  assert.match(html, /<button[^>]*aria-pressed="true"[^>]*>Char range<\/button>/);
  assert.match(html, /<button[^>]*aria-pressed="false"[^>]*>Block ID<\/button>/);
  assert.match(html, /Last poll tick/);
  assert.match(html, /Last idempotency key: screenshot-123/);
});
