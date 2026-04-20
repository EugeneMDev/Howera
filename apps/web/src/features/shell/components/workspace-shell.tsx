"use client";

import React, { type ReactNode } from "react";

import { usePathname } from "next/navigation";

import { WorkspaceShellFrame } from "@/features/shell/components/workspace-shell-frame";
import { useApiClient, useQueryVersion, useRuntimeConfig } from "@/shared/providers/app-providers";

interface WorkspaceShellProps {
  children: ReactNode;
}

export function WorkspaceShell({ children }: WorkspaceShellProps) {
  const pathname = usePathname();
  const runtimeConfig = useRuntimeConfig();
  const foundationQueryVersion = useQueryVersion("foundation");
  const apiClient = useApiClient();

  return (
    <WorkspaceShellFrame
      appEnv={runtimeConfig.appEnv}
      foundationQueryVersion={foundationQueryVersion}
      hasApiClient={typeof apiClient.request === "function"}
      hostingTarget={runtimeConfig.hostingTarget}
      missingRuntimeKeys={runtimeConfig.missingKeys}
      pathname={pathname}
      telemetryEnabled={runtimeConfig.telemetryEnabled}
    >
      {children}
    </WorkspaceShellFrame>
  );
}
