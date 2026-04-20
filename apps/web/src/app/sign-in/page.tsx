import { Suspense } from "react";

import { AuthStatusCard } from "@/features/auth/components/auth-status-card";
import { SignInScreen } from "@/features/auth/components/sign-in-screen";
import { Panel } from "@/shared/ui/panel";

export default function SignInPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto flex min-h-screen w-full max-w-4xl items-center px-4 py-8">
          <Panel variant="strong" className="w-full">
            <AuthStatusCard
              description="Preparing Firebase sign-in parameters."
              mode="loading"
              title="Loading sign-in"
            />
          </Panel>
        </div>
      }
    >
      <SignInScreen />
    </Suspense>
  );
}
