import {
  buildAuthRedirectUrl,
  safeNextPath,
} from "./auth-callback.ts";

const fallbackOrigin = "https://1c48b89a3342";
const forwardedHeaders = new Headers({
  "x-forwarded-host": "icy-wave-0b54d110f.7.azurestaticapps.net",
  "x-forwarded-proto": "https",
});

const forwardedRedirect = buildAuthRedirectUrl({
  fallbackOrigin,
  headers: forwardedHeaders,
  nextPath: "/onboarding",
});

if (forwardedRedirect !== "https://icy-wave-0b54d110f.7.azurestaticapps.net/onboarding") {
  throw new Error("Auth callback redirects should prefer the public forwarded host.");
}

const configuredRedirect = buildAuthRedirectUrl({
  fallbackOrigin,
  headers: new Headers(),
  nextPath: "/onboarding",
  publicSiteUrl: "https://icy-wave-0b54d110f.7.azurestaticapps.net/",
});

if (configuredRedirect !== "https://icy-wave-0b54d110f.7.azurestaticapps.net/onboarding") {
  throw new Error("Auth callback redirects should prefer the configured public site URL.");
}

if (safeNextPath("https://evil.example") !== "/") {
  throw new Error("Auth callback should reject absolute next URLs.");
}

if (safeNextPath("//evil.example") !== "/") {
  throw new Error("Auth callback should reject protocol-relative next URLs.");
}
