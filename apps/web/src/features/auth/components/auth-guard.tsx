"use client";

import React, { useEffect, type ReactNode } from "react";

import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/features/auth/auth-provider";
import { AuthStatusCard } from "@/features/auth/components/auth-status-card";
import { buildSignInPath } from "@/features/auth/redirect";
import { Panel } from "@/shared/ui/panel";

interface AuthGuardProps {
  children: ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const auth = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (auth.status === "unauthenticated") {
      router.replace(buildSignInPath(pathname));
    }
  }, [auth.status, pathname, router]);

  if (auth.status === "loading") {
    return (
      <Panel variant="strong">
        <AuthStatusCard
          description="Checking Firebase session state before protected workspace routes render."
          mode="loading"
          title="Restoring your workspace session"
        />
      </Panel>
    );
  }

  if (auth.status === "error") {
    return (
      <Panel variant="strong">
        <AuthStatusCard
          actionLabel="Retry sign-in"
          description={auth.error ?? "The sign-in flow could not be completed."}
          mode="error"
          onAction={() => {
            void auth.signIn();
          }}
          title="Authentication needs attention"
        />
      </Panel>
    );
  }

  if (auth.status === "unauthenticated") {
    return (
      <Panel variant="strong">
        <AuthStatusCard
          description="Protected workspace routes require Google sign-in. Redirecting now."
          mode="redirecting"
          title="Redirecting to sign-in"
        />
      </Panel>
    );
  }

  return <>{children}</>;
}
