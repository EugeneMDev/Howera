import type { ApiClient } from "@/shared/api/client";

export interface Project {
  id: string;
  name: string;
  created_at: string;
}

export interface CreateProjectInput {
  name: string;
}

export async function listProjects(apiClient: ApiClient): Promise<Project[]> {
  return apiClient.get<Project[]>("/projects", { auth: "required" });
}

export async function createProject(
  apiClient: ApiClient,
  input: CreateProjectInput,
): Promise<Project> {
  return apiClient.post<Project>("/projects", { name: input.name }, { auth: "required" });
}

export async function getProject(apiClient: ApiClient, projectId: string): Promise<Project> {
  return apiClient.get<Project>(`/projects/${projectId}`, { auth: "required" });
}
