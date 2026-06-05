import {
  buildAuthCallbackUrl,
  microsoftOAuthOptions,
} from "./microsoft-oauth.ts";

const callbackUrl = buildAuthCallbackUrl("https://app.example", "/onboarding");

if (callbackUrl !== "https://app.example/auth/callback?next=%2Fonboarding") {
  throw new Error("Auth callback URL should preserve the post-login destination.");
}

const options = microsoftOAuthOptions("https://app.example/onboarding");

if (options.redirectTo !== "https://app.example/onboarding") {
  throw new Error("Microsoft OAuth redirectTo should use the provided redirect URL.");
}

if (options.scopes !== "openid profile email User.Read") {
  throw new Error("Microsoft OAuth scopes should include only the profile and Graph user scopes needed for sign-in.");
}

if (options.scopes.includes("offline_access")) {
  throw new Error("Microsoft OAuth should not request offline_access because provider refresh tokens inflate auth cookies.");
}

if (options.queryParams?.prompt !== "select_account") {
  throw new Error("Microsoft OAuth should force Microsoft account selection.");
}
