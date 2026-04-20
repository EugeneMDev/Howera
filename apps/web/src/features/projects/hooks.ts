"use client";

import { useEffect, useState } from "react";

import { isNoLeakNotFoundError } from "@/shared/api/errors";
import {
  useApiClient,
  useInvalidateQuery,
  useQueryVersion,
  useTelemetry,
} from "@/shared/providers/app-providers";
import { createProject, getProject, listProjects, type Project } from "@/features/projects/api";

type QueryStatus = "loading" | "success" | "error";
type MutationStatus = "idle" | "submitting" | "error";

interface ProjectsListState {
  error: string | null;
  projects: Project[];
  status: QueryStatus;
}

interface ProjectDetailState {
  error: string | null;
  notFound: boolean;
  project: Project | null;
  status: QueryStatus;
}

function toErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}

export const PROJECTS_QUERY_KEY = "projects:list";

export function projectDetailQueryKey(projectId: string): string {
  return `projects:${projectId}`;
}

export function useProjectsList() {
  const apiClient = useApiClient();
  const queryVersion = useQueryVersion(PROJECTS_QUERY_KEY);
  const invalidateQuery = useInvalidateQuery();
  const [state, setState] = useState<ProjectsListState>({
    error: null,
    projects: [],
    status: "loading",
  });

  useEffect(() => {
    let cancelled = false;

    setState((current) => ({
      ...current,
      error: null,
      status: current.projects.length > 0 ? current.status : "loading",
    }));

    void listProjects(apiClient)
      .then((projects) => {
        if (cancelled) {
          return;
        }

        setState({
          error: null,
          projects,
          status: "success",
        });
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }

        setState({
          error: toErrorMessage(error, "Projects could not be loaded."),
          projects: [],
          status: "error",
        });
      });

    return () => {
      cancelled = true;
    };
  }, [apiClient, queryVersion]);

  return {
    ...state,
    refresh() {
      invalidateQuery(PROJECTS_QUERY_KEY);
    },
  };
}

export function useCreateProject() {
  const apiClient = useApiClient();
  const invalidateQuery = useInvalidateQuery();
  const telemetry = useTelemetry();
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<MutationStatus>("idle");

  return {
    error,
    isSubmitting: status === "submitting",
    async submit(name: string): Promise<Project | null> {
      const normalizedName = name.trim();
      if (!normalizedName) {
        setError("Project name is required.");
        setStatus("error");
        return null;
      }

      try {
        setError(null);
        setStatus("submitting");
        const project = await createProject(apiClient, { name: normalizedName });
        invalidateQuery(PROJECTS_QUERY_KEY);
        invalidateQuery(projectDetailQueryKey(project.id));
        telemetry.track({
          attributes: {
            action: "create",
            projectId: project.id,
            result: "succeeded",
          },
          name: "project.create.succeeded",
        });
        setStatus("idle");
        return project;
      } catch (submitError) {
        telemetry.track({
          attributes: {
            action: "create",
            result: "failed",
          },
          error: submitError,
          name: "project.create.failed",
        });
        setError(toErrorMessage(submitError, "Project could not be created."));
        setStatus("error");
        return null;
      }
    },
  };
}

export function useProjectDetail(projectId: string) {
  const apiClient = useApiClient();
  const invalidateQuery = useInvalidateQuery();
  const queryVersion = useQueryVersion(projectDetailQueryKey(projectId));
  const [state, setState] = useState<ProjectDetailState>({
    error: null,
    notFound: false,
    project: null,
    status: "loading",
  });

  useEffect(() => {
    let cancelled = false;

    setState((current) => ({
      ...current,
      error: null,
      notFound: false,
      status: current.project ? current.status : "loading",
    }));

    void getProject(apiClient, projectId)
      .then((project) => {
        if (cancelled) {
          return;
        }

        setState({
          error: null,
          notFound: false,
          project,
          status: "success",
        });
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }

        if (isNoLeakNotFoundError(error)) {
          setState({
            error: null,
            notFound: true,
            project: null,
            status: "error",
          });
          return;
        }

        setState({
          error: toErrorMessage(error, "Project details could not be loaded."),
          notFound: false,
          project: null,
          status: "error",
        });
      });

    return () => {
      cancelled = true;
    };
  }, [apiClient, projectId, queryVersion]);

  return {
    ...state,
    refresh() {
      invalidateQuery(projectDetailQueryKey(projectId));
    },
  };
}
