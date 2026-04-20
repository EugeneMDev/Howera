import assert from "node:assert/strict";
import test from "node:test";

import type { ApiClient, ApiRequestOptions } from "../../src/shared/api/client";
import { createProject, getProject, listProjects, type Project } from "../../src/features/projects/api";

function createMockApiClient() {
  const calls: Array<{
    body?: ApiRequestOptions["body"];
    method: "get" | "post";
    options?: ApiRequestOptions | Omit<ApiRequestOptions, "method" | "body">;
    path: string;
  }> = [];

  const apiClient: ApiClient = {
    async get<T>(path: string, options?: Omit<ApiRequestOptions, "method" | "body">): Promise<T> {
      calls.push({ method: "get", options, path });
      return [] as T;
    },
    async post<T>(
      path: string,
      body?: ApiRequestOptions["body"],
      options?: Omit<ApiRequestOptions, "method" | "body">,
    ): Promise<T> {
      calls.push({ body, method: "post", options, path });
      return { id: "project-123", name: "Demo Project", created_at: "2026-03-24T10:00:00Z" } as T;
    },
    async request<T>(path: string): Promise<T> {
      void path;
      throw new Error("request should not be called directly in project API tests");
    },
  };

  return { apiClient, calls };
}

test("project API uses contract paths and required auth", async () => {
  const { apiClient, calls } = createMockApiClient();

  await listProjects(apiClient);
  const createdProject = await createProject(apiClient, { name: "Demo Project" });
  await getProject(apiClient, "project-123");

  assert.deepEqual(calls, [
    { method: "get", options: { auth: "required" }, path: "/projects" },
    {
      body: { name: "Demo Project" },
      method: "post",
      options: { auth: "required" },
      path: "/projects",
    },
    { method: "get", options: { auth: "required" }, path: "/projects/project-123" },
  ]);
  assert.deepEqual(createdProject, {
    id: "project-123",
    name: "Demo Project",
    created_at: "2026-03-24T10:00:00Z",
  } satisfies Project);
});
