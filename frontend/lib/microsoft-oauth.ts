export function buildAuthCallbackUrl(origin: string, nextPath: string) {
  const url = new URL("/auth/callback", origin);
  url.searchParams.set("next", nextPath.startsWith("/") ? nextPath : "/");
  return url.toString();
}

export function microsoftOAuthOptions(redirectTo: string) {
  return {
    redirectTo,
    scopes: "openid profile email User.Read",
    queryParams: {
      prompt: "select_account",
    },
  };
}
