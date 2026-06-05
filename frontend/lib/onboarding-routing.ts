import type { UserOnboardingStatus } from "@/lib/api";

export function getPostAuthRedirectPath(status: UserOnboardingStatus) {
  return status.onboarding_completed ? "/" : "/onboarding";
}
