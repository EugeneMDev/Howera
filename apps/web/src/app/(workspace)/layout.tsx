import type { ReactNode } from "react";

import { AuthGuard } from "@/features/auth/components/auth-guard";
import { WorkspaceShell } from "@/features/shell/components/workspace-shell";

interface WorkspaceLayoutProps {
  children: ReactNode;
}

export default function WorkspaceLayout({ children }: WorkspaceLayoutProps) {
  return (
    <AuthGuard>
      <WorkspaceShell>{children}</WorkspaceShell>
    </AuthGuard>
  );
}
