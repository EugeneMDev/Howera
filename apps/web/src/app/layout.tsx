import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AuthProvider } from "@/features/auth/auth-provider";
import { AppProviders } from "@/shared/providers/app-providers";

import "./globals.css";

export const metadata: Metadata = {
  title: "Howera",
  description: "Frontend workspace for Howera's deterministic authoring workflow.",
};

interface RootLayoutProps {
  children: ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <AppProviders>{children}</AppProviders>
        </AuthProvider>
      </body>
    </html>
  );
}
