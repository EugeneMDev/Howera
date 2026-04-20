import React, { type ReactNode } from "react";

import Link from "next/link";

import {
  isActiveWorkspacePath,
  workspaceChecklist,
  workspaceNavigation,
  workspaceSignals,
} from "@/features/shell/config/navigation";
import { cn } from "@/shared/lib/cn";
import { Panel, PanelDescription, PanelHeader, PanelTitle } from "@/shared/ui/panel";
import { StatusPill } from "@/shared/ui/status-pill";

interface WorkspaceShellFrameProps {
  appEnv?: string;
  children: ReactNode;
  foundationQueryVersion?: number;
  hasApiClient?: boolean;
  hostingTarget?: string;
  missingRuntimeKeys?: string[];
  pathname: string;
  telemetryEnabled?: boolean;
}

export function WorkspaceShellFrame({
  appEnv = "development",
  children,
  foundationQueryVersion = 0,
  hasApiClient = false,
  hostingTarget = "firebase-hosting",
  missingRuntimeKeys = [],
  pathname,
  telemetryEnabled = false,
}: WorkspaceShellFrameProps) {
  const runtimeReady = missingRuntimeKeys.length === 0;

  return (
    <div className="relative min-h-screen overflow-hidden">
      <a href="#workspace-content" className="skip-link focus-ring">
        Skip to workspace content
      </a>

      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(circle_at_top,_rgba(197,98,49,0.18),_transparent_62%)]"
      />

      <div className="relative mx-auto flex min-h-screen max-w-[1600px] flex-col gap-4 px-4 py-4 lg:px-6 lg:py-6">
        <header className="surface-panel-strong rounded-[var(--radius-panel)] px-5 py-5 lg:px-7">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p className="eyebrow text-[var(--brand-primary-strong)]">Howera editorial studio</p>
              <h1 className="display-title mt-3 text-4xl font-semibold text-[var(--text-primary)] md:text-5xl">
                Frontend foundation with a workspace-first shell.
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-[var(--text-secondary)] md:text-base">
                Story 7.1 establishes the three-zone layout, tokenized styling, and reusable base
                primitives that later auth, projects, job lifecycle, and editor flows will share.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <StatusPill tone="info">Story 7.1</StatusPill>
              <StatusPill tone="success">Theme tokens live</StatusPill>
              <StatusPill tone={runtimeReady ? "success" : "danger"}>
                {runtimeReady ? "Runtime env wired" : `Missing env ${missingRuntimeKeys.length}`}
              </StatusPill>
            </div>
          </div>
        </header>

        <div className="grid flex-1 gap-4 lg:grid-cols-[280px_minmax(0,1fr)] xl:grid-cols-[280px_minmax(0,1fr)_320px]">
          <aside className="lg:sticky lg:top-6 lg:self-start" aria-labelledby="workspace-navigation-title">
            <Panel className="h-full">
              <PanelHeader>
                <p className="eyebrow text-[var(--text-muted)]">Workspace map</p>
                <PanelTitle id="workspace-navigation-title" className="text-[1.35rem]">
                  Primary navigation
                </PanelTitle>
                <PanelDescription>
                  Each route keeps the same mental model: projects, jobs, and instruction work all
                  happen inside one persistent shell.
                </PanelDescription>
              </PanelHeader>

              <nav aria-label="Primary workspace navigation" className="space-y-2">
                {workspaceNavigation.map((item) => {
                  const active = isActiveWorkspacePath(pathname, item.href);

                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "focus-ring block rounded-[var(--radius-card)] px-4 py-4 transition-colors",
                        active
                          ? "bg-[var(--brand-soft)] text-[var(--brand-primary-strong)]"
                          : "hover:bg-[rgba(84,70,49,0.06)]",
                      )}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="display-title text-xl font-semibold">{item.label}</span>
                        {active ? <StatusPill tone="info">Active</StatusPill> : null}
                      </div>
                      <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
                        {item.description}
                      </p>
                    </Link>
                  );
                })}
              </nav>
            </Panel>
          </aside>

          <main id="workspace-content" tabIndex={-1} className="min-w-0" aria-label="Workspace content">
            {children}
          </main>

          <aside className="space-y-4 lg:col-span-2 xl:col-span-1" aria-labelledby="context-panel-title">
            <Panel variant="strong">
              <PanelHeader>
                <p className="eyebrow text-[var(--text-muted)]">Operational context</p>
                <PanelTitle id="context-panel-title" className="text-[1.35rem]">
                  Shared shell contract
                </PanelTitle>
                <PanelDescription>
                  The right rail stays available for lifecycle state, task polling, transcript
                  context, and export provenance as the product grows.
                </PanelDescription>
              </PanelHeader>

              <div className="space-y-4">
                {workspaceSignals.map((signal) => (
                  <div key={signal.label} className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
                    <p className="eyebrow text-[var(--brand-primary-strong)]">{signal.label}</p>
                    <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                      {signal.value}
                    </p>
                  </div>
                ))}
              </div>
            </Panel>

            <Panel variant="muted">
              <PanelHeader>
                <p className="eyebrow text-[var(--text-muted)]">Provider status</p>
                <PanelTitle className="text-[1.2rem]">Foundation wiring</PanelTitle>
              </PanelHeader>

              <div className="space-y-3 text-sm leading-6 text-[var(--text-secondary)]">
                <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
                  <p className="eyebrow text-[var(--text-muted)]">API client</p>
                  <p className="mt-2">
                    {hasApiClient
                      ? "Shared client provider is mounted for workspace routes."
                      : "Shared client provider is not mounted yet."}
                  </p>
                </div>

                <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
                  <p className="eyebrow text-[var(--text-muted)]">Query namespace</p>
                  <p className="mt-2">Foundation query revision: {foundationQueryVersion}</p>
                </div>

                <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
                  <p className="eyebrow text-[var(--text-muted)]">Runtime config</p>
                  <p className="mt-2">
                    {runtimeReady
                      ? "Required public runtime variables are available to the app shell."
                      : `Missing keys: ${missingRuntimeKeys.join(", ")}`}
                  </p>
                </div>

                <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
                  <p className="eyebrow text-[var(--text-muted)]">Deployment target</p>
                  <p className="mt-2">
                    {hostingTarget} for the {appEnv} environment.
                  </p>
                </div>

                <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
                  <p className="eyebrow text-[var(--text-muted)]">Telemetry posture</p>
                  <p className="mt-2">
                    {telemetryEnabled
                      ? "Safe telemetry emission is enabled with sanitized browser events."
                      : "Safe telemetry hooks are wired, but emission is disabled for this environment."}
                  </p>
                </div>
              </div>
            </Panel>

            <Panel variant="muted">
              <PanelHeader>
                <p className="eyebrow text-[var(--text-muted)]">Readiness</p>
                <PanelTitle className="text-[1.2rem]">What this story establishes</PanelTitle>
              </PanelHeader>

              <ul className="space-y-3 text-sm leading-6 text-[var(--text-secondary)]">
                {workspaceChecklist.map((item) => (
                  <li key={item} className="flex items-start gap-3">
                    <span
                      aria-hidden="true"
                      className="mt-1 h-2.5 w-2.5 rounded-full bg-[var(--brand-primary)]"
                    />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </Panel>
          </aside>
        </div>
      </div>
    </div>
  );
}
