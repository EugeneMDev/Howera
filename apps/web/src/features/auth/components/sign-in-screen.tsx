"use client";

import React, { useEffect, useState } from "react";

import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/features/auth/auth-provider";
import { AuthStatusCard } from "@/features/auth/components/auth-status-card";
import { normalizeNextPath } from "@/features/auth/redirect";
import { useRuntimeConfig } from "@/shared/providers/app-providers";
import { Panel, PanelDescription, PanelHeader, PanelTitle } from "@/shared/ui/panel";

export function SignInScreen() {
  const auth = useAuth();
  const runtimeConfig = useRuntimeConfig();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [redirectStarted, setRedirectStarted] = useState(false);
  const nextPath = normalizeNextPath(searchParams.get("next"));
  const isMockAuth = runtimeConfig.authProvider === "mock";

  useEffect(() => {
    if (auth.status === "authenticated") {
      router.replace(nextPath);
    }
  }, [auth.status, nextPath, router]);

  useEffect(() => {
    if (auth.status === "unauthenticated" && !auth.error && !redirectStarted) {
      setRedirectStarted(true);
      void auth.signIn();
    }
  }, [auth, redirectStarted]);

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-4xl items-center px-4 py-8">
      <Panel variant="strong" className="w-full">
        <PanelHeader>
          <p className="eyebrow text-[var(--brand-primary-strong)]">Workspace access</p>
          <PanelTitle>{isMockAuth ? "Local development access" : "Sign in with Google"}</PanelTitle>
          <PanelDescription>
            {isMockAuth
              ? "Howera is using a deterministic local mock identity for protected workspace routes."
              : "Howera uses Firebase session restore and bearer-authenticated API calls for protected workspace routes."}
          </PanelDescription>
        </PanelHeader>

        {auth.status === "loading" ? (
          <AuthStatusCard
            description={
              isMockAuth
                ? "Preparing the local development identity before entering the workspace."
                : "Checking for a persisted Firebase session before redirecting."
            }
            mode="loading"
            title={isMockAuth ? "Preparing local access" : "Restoring previous session"}
          />
        ) : auth.status === "authenticated" ? (
          <AuthStatusCard
            description={
              isMockAuth
                ? `Continuing to ${nextPath} with your local development identity.`
                : `Returning to ${nextPath} with your restored session.`
            }
            mode="redirecting"
            title="Returning to the workspace"
          />
        ) : auth.error ? (
          <AuthStatusCard
            actionLabel={isMockAuth ? "Retry local access" : "Try Google sign-in again"}
            description={auth.error}
            mode="error"
            onAction={() => {
              void auth.signIn();
            }}
            title={isMockAuth ? "Local access failed" : "Sign-in failed"}
          />
        ) : (
          <AuthStatusCard
            description={
              isMockAuth
                ? "Starting the local development session now."
                : "Starting the Google redirect flow now."
            }
            mode="redirecting"
            title={isMockAuth ? "Continuing locally" : "Redirecting to Google"}
          />
        )}
      </Panel>
    </div>
  );
}
