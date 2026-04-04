"use client";

import React from "react";
import Link from "next/link";

import { LoadingState, ErrorState } from "@/shared/ui/async-state";
import { Button } from "@/shared/ui/button";
import { formatDateTime } from "@/shared/lib/format-date";
import { Panel, PanelDescription, PanelHeader, PanelTitle } from "@/shared/ui/panel";
import { NoLeakNotFoundState } from "@/shared/ui/no-leak-not-found-state";
import { useProjectDetail } from "@/features/projects/hooks";

interface ProjectDetailScreenProps {
  projectId: string;
}

export function ProjectDetailScreen({ projectId }: ProjectDetailScreenProps) {
  const { error, notFound, project, refresh, status } = useProjectDetail(projectId);

  if (status === "loading") {
    return (
      <Panel variant="strong">
        <LoadingState
          description="Loading project metadata for this owner-scoped route."
          title="Fetching project"
        />
      </Panel>
    );
  }

  if (notFound) {
    return (
      <Panel variant="strong">
        <NoLeakNotFoundState resourceName="project" />
      </Panel>
    );
  }

  if (!project || status === "error") {
    return (
      <Panel variant="strong">
        <ErrorState
          action={
            <Button
              size="compact"
              variant="secondary"
              onClick={() => {
                refresh();
              }}
            >
              Retry
            </Button>
          }
          description={error ?? "Project details could not be loaded."}
          title="Project detail unavailable"
        />
      </Panel>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Panel variant="strong">
        <PanelHeader>
          <p className="eyebrow text-[var(--brand-primary-strong)]">Project detail</p>
          <PanelTitle className="text-4xl">{project.name}</PanelTitle>
          <PanelDescription>
            Contract identifier: {project.id}. Created {formatDateTime(project.created_at)}.
          </PanelDescription>
        </PanelHeader>

        <div className="flex flex-wrap gap-4 text-sm font-medium">
          <Link
            className="text-[var(--brand-primary-strong)] hover:underline"
            href={`/projects/${project.id}/jobs`}
          >
            Open project jobs
          </Link>
          <Link className="text-[var(--brand-primary-strong)] hover:underline" href="/projects">
            Back to project list
          </Link>
        </div>
      </Panel>

      <Panel>
        <PanelHeader>
          <p className="eyebrow text-[var(--text-muted)]">Navigation contract</p>
          <PanelTitle>Thin page, feature-owned data</PanelTitle>
          <PanelDescription>
            This route resolves `GET /projects/{projectId}` and delegates job creation/browsing to
            the nested project-jobs route.
          </PanelDescription>
        </PanelHeader>
      </Panel>
    </div>
  );
}
