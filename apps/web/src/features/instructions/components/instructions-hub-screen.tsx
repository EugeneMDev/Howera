"use client";

import { useState } from "react";

import { useRouter } from "next/navigation";

import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Panel, PanelDescription, PanelHeader, PanelTitle } from "@/shared/ui/panel";
import { StatusPill } from "@/shared/ui/status-pill";

export function InstructionsHubScreen() {
  const router = useRouter();
  const [instructionId, setInstructionId] = useState("");
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="flex flex-col gap-4">
      <Panel variant="strong">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="eyebrow text-[var(--brand-primary-strong)]">Instruction editor</p>
            <h2 className="display-title mt-3 text-4xl font-semibold">
              Open one instruction and stay inside the shell.
            </h2>
            <p className="mt-4 text-sm leading-6 text-[var(--text-secondary)] md:text-base">
              The API exposes direct instruction detail and version-safe update endpoints, not a
              global instruction list. This workspace opens an exact `instruction_id` and keeps
              optimistic-concurrency handling visible while you edit.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <StatusPill tone="info">Story 8.1</StatusPill>
            <StatusPill tone="success">Version-safe save</StatusPill>
          </div>
        </div>
      </Panel>

      <div className="grid gap-4 2xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
        <Panel>
          <PanelHeader>
            <p className="eyebrow text-[var(--text-muted)]">Open by contract id</p>
            <PanelTitle>Load a specific instruction</PanelTitle>
            <PanelDescription>
              Use the exact `instruction_id` returned by backend workflows. The editor route is
              deterministic: `/instructions/[instructionId]`.
            </PanelDescription>
          </PanelHeader>

          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault();

              const normalizedInstructionId = instructionId.trim();
              if (!normalizedInstructionId) {
                setError("Instruction ID is required.");
                return;
              }

              setError(null);
              router.push(`/instructions/${encodeURIComponent(normalizedInstructionId)}`);
            }}
          >
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">
                Instruction ID
              </span>
              <Input
                autoComplete="off"
                name="instructionId"
                onChange={(event) => setInstructionId(event.currentTarget.value)}
                placeholder="inst-123"
                value={instructionId}
              />
            </label>

            {error ? (
              <div className="rounded-[var(--radius-card)] bg-[var(--status-danger-soft)] px-4 py-3 text-sm text-[var(--status-danger)]">
                {error}
              </div>
            ) : null}

            <div className="flex flex-wrap gap-3">
              <Button type="submit">Open instruction editor</Button>
            </div>
          </form>
        </Panel>

        <Panel variant="muted">
          <PanelHeader>
            <p className="eyebrow text-[var(--text-muted)]">What 8.1 adds</p>
            <PanelTitle>Editing posture</PanelTitle>
          </PanelHeader>

          <div className="space-y-4 text-sm leading-6 text-[var(--text-secondary)]">
            <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
              <p className="eyebrow text-[var(--brand-primary-strong)]">Safe save</p>
              <p className="mt-2">
                Saves submit `base_version` and update the editor in place when the API accepts the
                new markdown.
              </p>
            </div>

            <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
              <p className="eyebrow text-[var(--brand-primary-strong)]">Conflict recovery</p>
              <p className="mt-2">
                On `VERSION_CONFLICT`, local draft content stays in the editor and the latest server
                version becomes available for reload or manual merge.
              </p>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}
