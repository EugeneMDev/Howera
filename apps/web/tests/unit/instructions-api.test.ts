import assert from "node:assert/strict";
import test from "node:test";

import type { ApiClient, ApiRequestOptions } from "../../src/shared/api/client";
import {
  getRegenerateTask,
  getInstruction,
  parseVersionConflictDetails,
  requestInstructionRegenerate,
  updateInstruction,
  type Instruction,
} from "../../src/features/instructions/api";

function createMockApiClient() {
  const calls: Array<{
    body?: ApiRequestOptions["body"];
    method: "get" | "post" | "request";
    options?: ApiRequestOptions;
    path: string;
  }> = [];

  const instruction: Instruction = {
    instruction_id: "inst-123",
    job_id: "job-123",
    markdown: "# Demo",
    updated_at: "2026-03-25T08:00:00Z",
    validation_status: "PASS",
    version: 2,
  };

  const apiClient: ApiClient = {
    async get<T>(path: string, options?: Omit<ApiRequestOptions, "method" | "body">): Promise<T> {
      calls.push({ method: "get", options, path });
      return instruction as T;
    },
    async post<T>(
      path: string,
      body?: ApiRequestOptions["body"],
      options?: Omit<ApiRequestOptions, "method" | "body">,
    ): Promise<T> {
      calls.push({ body, method: "post", options, path });
      return {
        id: "task-123",
        instruction_id: "inst-123",
        progress_pct: 10,
        replayed: false,
        requested_at: "2026-03-25T10:00:00Z",
        status: "PENDING",
      } as T;
    },
    async request<T>(path: string, options?: ApiRequestOptions): Promise<T> {
      calls.push({ method: "request", options, path });
      return instruction as T;
    },
  };

  return { apiClient, calls, instruction };
}

test("instruction API uses contract paths and optimistic concurrency payloads", async () => {
  const { apiClient, calls, instruction } = createMockApiClient();

  const loadedInstruction = await getInstruction(apiClient, "inst-123");
  await getInstruction(apiClient, "inst-123", { version: 2 });
  const updatedInstruction = await updateInstruction(apiClient, "inst-123", {
    base_version: 2,
    markdown: "# Updated",
  });
  await requestInstructionRegenerate(apiClient, "inst-123", {
    base_version: 2,
    client_request_id: "regen-123",
    selection: {
      char_range: {
        end_offset: 12,
        start_offset: 4,
      },
    },
  });
  await getRegenerateTask(apiClient, "task-123");

  assert.deepEqual(calls, [
    { method: "get", options: { auth: "required" }, path: "/instructions/inst-123" },
    { method: "get", options: { auth: "required" }, path: "/instructions/inst-123?version=2" },
    {
      method: "request",
      options: {
        auth: "required",
        body: { base_version: 2, markdown: "# Updated" },
        method: "PUT",
      },
      path: "/instructions/inst-123",
    },
    {
      body: {
        base_version: 2,
        client_request_id: "regen-123",
        context: undefined,
        model_profile: undefined,
        prompt_params_ref: undefined,
        prompt_template_id: undefined,
        selection: {
          char_range: {
            end_offset: 12,
            start_offset: 4,
          },
        },
      },
      method: "post",
      options: { auth: "required" },
      path: "/instructions/inst-123/regenerate",
    },
    { method: "get", options: { auth: "required" }, path: "/tasks/task-123" },
  ]);
  assert.deepEqual(loadedInstruction, instruction);
  assert.deepEqual(updatedInstruction, instruction);
});

test("instruction API parses version conflict details conservatively", () => {
  assert.deepEqual(parseVersionConflictDetails({ base_version: 2, current_version: 3 }), {
    base_version: 2,
    current_version: 3,
  });
  assert.equal(parseVersionConflictDetails({ base_version: "2", current_version: 3 }), null);
  assert.equal(parseVersionConflictDetails(null), null);
});
