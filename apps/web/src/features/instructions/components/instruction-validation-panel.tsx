"use client";

import React from "react";

import type { Instruction } from "@/features/instructions/api";
import { formatDateTime } from "@/shared/lib/format-date";
import { Panel, PanelDescription, PanelHeader, PanelTitle } from "@/shared/ui/panel";
import { StatusPill } from "@/shared/ui/status-pill";

function getValidationTone(status: "PASS" | "FAIL") {
  return status === "PASS" ? "success" : "warning";
}

function getValidationSummary(instruction: Instruction): string {
  if (instruction.validated_at) {
    return `Last validated ${formatDateTime(instruction.validated_at)}.`;
  }

  return "Validation timestamp is not available yet.";
}

export function InstructionValidationPanel({
  instruction,
  latestServerVersion,
}: {
  instruction: Instruction;
  latestServerVersion: number;
}) {
  const validationErrors = instruction.validation_errors ?? [];
  const validationStateCopy =
    instruction.validation_status === "PASS"
      ? "Backend validation passed for the currently loaded instruction snapshot."
      : validationErrors.length > 0
        ? `Backend validation reported ${validationErrors.length} structured issue${validationErrors.length === 1 ? "" : "s"} for this instruction version.`
        : "Backend validation failed for this instruction version, but the API did not attach structured validation errors.";

  return (
    <div className="space-y-4">
      <Panel variant="muted">
        <PanelHeader>
          <p className="eyebrow text-[var(--text-muted)]">Validation state</p>
          <PanelTitle>Server-authored quality signal</PanelTitle>
          <PanelDescription>
            Validation metadata updates after save or regenerate responses without adding
            client-side heuristics.
          </PanelDescription>
        </PanelHeader>

        <div className="space-y-4 text-sm leading-6 text-[var(--text-secondary)]">
          <div className="flex flex-wrap items-center gap-2">
            <StatusPill tone={getValidationTone(instruction.validation_status)}>
              {instruction.validation_status}
            </StatusPill>
            <StatusPill tone="info">v{instruction.version}</StatusPill>
            {latestServerVersion > instruction.version ? (
              <StatusPill tone="warning">Latest known v{latestServerVersion}</StatusPill>
            ) : null}
          </div>

          <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
            <p>{validationStateCopy}</p>
            <p className="mt-2">{getValidationSummary(instruction)}</p>
            {instruction.validator_version ? (
              <p className="mt-2">Validator version: {instruction.validator_version}.</p>
            ) : null}
          </div>
        </div>
      </Panel>

      <Panel variant="muted">
        <PanelHeader>
          <p className="eyebrow text-[var(--text-muted)]">Validation issues</p>
          <PanelTitle>Structured backend feedback</PanelTitle>
          <PanelDescription>
            Editing remains available while these contract-provided issues are visible.
          </PanelDescription>
        </PanelHeader>

        {validationErrors.length === 0 ? (
          <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4 text-sm leading-6 text-[var(--text-secondary)]">
            {instruction.validation_status === "PASS"
              ? "No validation errors are attached to the currently loaded instruction version."
              : "No structured validation errors were returned for the current failing validation state."}
          </div>
        ) : (
          <div className="space-y-3">
            {validationErrors.map((issue, index) => (
              <div
                key={`${issue.code}-${issue.path ?? "root"}-${index}`}
                className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <h3 className="display-title text-lg font-semibold">{issue.code}</h3>
                  {issue.path ? <StatusPill tone="warning">{issue.path}</StatusPill> : null}
                </div>
                <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                  {issue.message}
                </p>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
