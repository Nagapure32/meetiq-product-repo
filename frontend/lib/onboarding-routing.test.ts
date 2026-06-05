import { getPostAuthRedirectPath } from "./onboarding-routing.ts";

if (
  getPostAuthRedirectPath({
    user_id: "user-1",
    onboarding_completed: true,
    onboarding_completed_at: "2026-06-05T10:00:00Z",
    calendar_connection_status: "connected",
    auto_join_enabled: true,
  }) !== "/"
) {
  throw new Error("Completed users should land on the dashboard.");
}

if (
  getPostAuthRedirectPath({
    user_id: "user-1",
    onboarding_completed: false,
    onboarding_completed_at: null,
    calendar_connection_status: "connected",
    auto_join_enabled: false,
  }) !== "/onboarding"
) {
  throw new Error("Incomplete users should land on onboarding.");
}
