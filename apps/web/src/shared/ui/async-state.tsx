import React, { type HTMLAttributes, type ReactNode } from "react";

import { cn } from "@/shared/lib/cn";
import { Button } from "@/shared/ui/button";

interface AsyncStateProps extends HTMLAttributes<HTMLDivElement> {
  action?: ReactNode;
  description: string;
  title: string;
  actionLabel?: string;
  actionHint?: string;
  decorativeSlot?: ReactNode;
}

function AsyncStateCard({
  action,
  actionHint,
  actionLabel,
  className,
  decorativeSlot,
  description,
  title,
  ...props
}: AsyncStateProps) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-card)] border bg-white/50 px-4 py-4",
        className,
      )}
      style={{ borderColor: "var(--line-subtle)" }}
      {...props}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="display-title text-xl font-semibold text-[var(--text-primary)]">
            {title}
          </h3>
          <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
            {description}
          </p>
        </div>

        {decorativeSlot}
      </div>

      {action ? (
        <div className="mt-4 flex flex-wrap items-center gap-3">{action}</div>
      ) : actionLabel ? (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button size="compact" variant="secondary">
            {actionLabel}
          </Button>
          {actionHint ? (
            <p className="text-xs uppercase tracking-[0.14em] text-[var(--text-muted)]">
              {actionHint}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function LoadingState({ description, title, ...props }: Omit<AsyncStateProps, "decorativeSlot">) {
  return (
    <AsyncStateCard
      description={description}
      title={title}
      decorativeSlot={
        <span
          aria-hidden="true"
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--status-info-soft)] text-[var(--status-info)]"
        >
          ...
        </span>
      }
      {...props}
    />
  );
}

export function EmptyState({
  action,
  actionHint,
  actionLabel,
  description,
  title,
  ...props
}: Omit<AsyncStateProps, "decorativeSlot">) {
  return (
    <AsyncStateCard
      action={action}
      actionHint={actionHint}
      actionLabel={actionLabel}
      description={description}
      title={title}
      decorativeSlot={
        <span
          aria-hidden="true"
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--brand-soft)] text-[var(--brand-primary-strong)]"
        >
          +
        </span>
      }
      {...props}
    />
  );
}

export function ErrorState({
  action,
  actionHint,
  actionLabel,
  description,
  title,
  ...props
}: Omit<AsyncStateProps, "decorativeSlot">) {
  return (
    <AsyncStateCard
      action={action}
      actionHint={actionHint}
      actionLabel={actionLabel}
      description={description}
      title={title}
      decorativeSlot={
        <span
          aria-hidden="true"
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--status-danger-soft)] text-[var(--status-danger)]"
        >
          !
        </span>
      }
      {...props}
    />
  );
}
