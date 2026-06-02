export function microsoftOAuthOptions(redirectTo: string) {
  return {
    redirectTo,
    scopes: "openid profile email offline_access User.Read",
    queryParams: {
      prompt: "select_account",
    },
  };
}
