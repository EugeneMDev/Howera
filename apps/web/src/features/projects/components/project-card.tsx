import React from "react";

import Link from "next/link";

import type { Project } from "@/features/projects/api";
import { formatDateTime } from "@/shared/lib/format-date";

interface ProjectCardProps {
  project: Project;
}

export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <article
      className="rounded-[var(--radius-card)] border bg-white/55 px-4 py-4"
      style={{ borderColor: "var(--line-subtle)" }}
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <p className="eyebrow text-[var(--text-muted)]">{project.id}</p>
          <h3 className="display-title mt-2 text-2xl font-semibold">{project.name}</h3>
          <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
            Created {formatDateTime(project.created_at)}
          </p>
        </div>

        <div className="flex flex-wrap gap-4 text-sm font-medium">
          <Link className="text-[var(--brand-primary-strong)] hover:underline" href={`/projects/${project.id}`}>
            Open project
          </Link>
          <Link
            className="text-[var(--brand-primary-strong)] hover:underline"
            href={`/projects/${project.id}/jobs`}
          >
            View jobs
          </Link>
        </div>
      </div>
    </article>
  );
}
