"use client";

import React from "react";

import { cn } from "@/shared/lib/cn";

export const instructionWorkspaceQuickLinks = [
  { href: "#instruction-draft-section", label: "Draft" },
  { href: "#instruction-anchor-section", label: "Anchors" },
  { href: "#instruction-screenshot-section", label: "Screenshots" },
  { href: "#instruction-export-section", label: "Exports" },
  { href: "#instruction-regenerate-section", label: "Regenerate" },
  { href: "#instruction-transcript-section", label: "Transcript" },
  { href: "#instruction-validation-section", label: "Validation" },
] as const;

export function InstructionWorkspaceQuickNav({ className }: { className?: string }) {
  return (
    <nav
      aria-label="Instruction workspace quick links"
      className={cn(
        "surface-panel-muted rounded-[var(--radius-panel)] px-4 py-4 lg:px-5",
        className,
      )}
    >
      <p className="eyebrow text-[var(--text-muted)]">Quick jump</p>
      <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
        On smaller screens, jump directly between the draft, task tools, transcript, and
        validation state without losing workspace context.
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        {instructionWorkspaceQuickLinks.map((item) => (
          <a
            key={item.href}
            href={item.href}
            className="focus-ring rounded-[var(--radius-pill)] bg-white/60 px-3 py-2 text-sm font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--brand-soft)]"
          >
            {item.label}
          </a>
        ))}
      </div>
    </nav>
  );
}
