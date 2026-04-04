import React from "react";

import Link from "next/link";

import { ErrorState } from "@/shared/ui/async-state";

interface NoLeakNotFoundStateProps {
  description?: string;
  resourceName: string;
  returnHref?: string;
  returnLabel?: string;
}

export function NoLeakNotFoundState({
  description,
  resourceName,
  returnHref = "/projects",
  returnLabel = "Back to projects",
}: NoLeakNotFoundStateProps) {
  return (
    <ErrorState
      action={
        <Link
          className="focus-ring inline-flex min-h-9 items-center justify-center rounded-[var(--radius-pill)] px-3 py-2 text-sm font-medium text-[var(--brand-primary-strong)] ring-1 ring-inset ring-[var(--line-strong)] transition-colors hover:bg-[var(--brand-soft)]"
          href={returnHref}
        >
          {returnLabel}
        </Link>
      }
      description={
        description ??
        `Howera uses the same not-found response for missing or unauthorized ${resourceName} records, so no cross-owner metadata is exposed here.`
      }
      title={`${resourceName} not found`}
    />
  );
}
