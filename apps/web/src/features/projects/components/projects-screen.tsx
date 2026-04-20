"use client";

import React, { useState } from "react";

import { EmptyState, ErrorState, LoadingState } from "@/shared/ui/async-state";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Panel, PanelDescription, PanelHeader, PanelTitle } from "@/shared/ui/panel";
import { ProjectCard } from "@/features/projects/components/project-card";
import { useCreateProject, useProjectsList } from "@/features/projects/hooks";

export function ProjectsScreen() {
  const { error, projects, refresh, status } = useProjectsList();
  const createProject = useCreateProject();
  const [projectName, setProjectName] = useState("");
  const [createdProjectId, setCreatedProjectId] = useState<string | null>(null);

  return (
    <div className="flex flex-col gap-4">
      <Panel variant="strong">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.7fr)]">
          <div className="max-w-3xl">
            <p className="eyebrow text-[var(--brand-primary-strong)]">Owned projects</p>
            <h2 className="display-title mt-3 text-4xl font-semibold">Create and browse workspace roots.</h2>
            <p className="mt-4 text-sm leading-6 text-[var(--text-secondary)] md:text-base">
              Project creation stays contract-first: the UI only sends a project name, then refreshes
              your owner-scoped list without a full page reload.
            </p>
          </div>

          <form
            className="rounded-[var(--radius-card)] border bg-white/55 p-4"
            style={{ borderColor: "var(--line-subtle)" }}
            onSubmit={(event) => {
              event.preventDefault();
              void createProject.submit(projectName).then((project) => {
                if (!project) {
                  return;
                }

                setProjectName("");
                setCreatedProjectId(project.id);
              });
            }}
          >
            <PanelHeader className="mb-4 gap-1">
              <p className="eyebrow text-[var(--text-muted)]">Create project</p>
              <PanelTitle className="text-2xl">New owned workspace</PanelTitle>
              <PanelDescription>
                The backend will assign the contract ID and `created_at` timestamp.
              </PanelDescription>
            </PanelHeader>

            <label className="block">
              <span className="mb-2 block text-sm font-medium text-[var(--text-secondary)]">
                Project name
              </span>
              <Input
                maxLength={120}
                placeholder="Demo Project"
                value={projectName}
                onChange={(event) => {
                  setProjectName(event.target.value);
                }}
              />
            </label>

            {createProject.error ? (
              <p className="mt-3 text-sm text-[var(--status-danger)]">{createProject.error}</p>
            ) : null}

            {createdProjectId ? (
              <p className="mt-3 text-sm text-[var(--status-success)]">
                Project created: {createdProjectId}
              </p>
            ) : null}

            <div className="mt-4 flex flex-wrap gap-3">
              <Button disabled={createProject.isSubmitting || projectName.trim().length === 0} type="submit">
                {createProject.isSubmitting ? "Creating project..." : "Create project"}
              </Button>
              <Button
                disabled={status === "loading"}
                type="button"
                variant="secondary"
                onClick={() => {
                  refresh();
                }}
              >
                Refresh list
              </Button>
            </div>
          </form>
        </div>
      </Panel>

      <Panel>
        <PanelHeader>
          <p className="eyebrow text-[var(--text-muted)]">Projects list</p>
          <PanelTitle>Owner-scoped records</PanelTitle>
          <PanelDescription>
            This surface is backed by `GET /projects` and only shows projects returned for the
            authenticated editor.
          </PanelDescription>
        </PanelHeader>

        {status === "loading" ? (
          <LoadingState
            description="Loading owned projects from the API."
            title="Fetching projects"
          />
        ) : status === "error" ? (
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
            description={error ?? "Projects could not be loaded."}
            title="Project list unavailable"
          />
        ) : projects.length === 0 ? (
          <EmptyState
            actionHint="Create the first owned project"
            actionLabel="Waiting for data"
            description="No projects were returned yet for this editor."
            title="No projects yet"
          />
        ) : (
          <div className="space-y-3">
            {projects.map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
