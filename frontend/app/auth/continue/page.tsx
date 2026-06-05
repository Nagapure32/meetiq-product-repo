"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { getUserOnboardingStatus } from "@/lib/api";
import { getPostAuthRedirectPath } from "@/lib/onboarding-routing";

export default function AuthContinuePage() {
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;

    async function redirectAfterAuth() {
      try {
        const status = await getUserOnboardingStatus();
        if (!cancelled) {
          router.replace(getPostAuthRedirectPath(status));
        }
      } catch {
        if (!cancelled) {
          router.replace("/onboarding");
        }
      }
    }

    void redirectAfterAuth();

    return () => {
      cancelled = true;
    };
  }, [router]);

  return (
    <main className="grid min-h-screen place-items-center bg-shell px-6 text-center">
      <div>
        <p className="text-sm font-semibold text-ink">Finishing sign in...</p>
        <p className="mt-2 text-xs leading-5 text-muted">Preparing your workspace.</p>
      </div>
    </main>
  );
}
