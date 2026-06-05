export function safeNextPath(value: string | null) {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return "/";
  }
  return value;
}

export function buildAuthRedirectUrl({
  fallbackOrigin,
  headers,
  nextPath,
  publicSiteUrl,
}: {
  fallbackOrigin: string;
  headers: Headers;
  nextPath: string;
  publicSiteUrl?: string;
}) {
  const origin =
    normalizeOrigin(publicSiteUrl) ??
    forwardedOrigin(headers) ??
    normalizeOrigin(fallbackOrigin) ??
    fallbackOrigin;

  return new URL(safeNextPath(nextPath), origin).toString();
}

function forwardedOrigin(headers: Headers) {
  const host = firstHeaderValue(headers.get("x-forwarded-host"));
  if (!host) {
    return null;
  }

  const proto = firstHeaderValue(headers.get("x-forwarded-proto")) ?? "https";
  return normalizeOrigin(`${proto}://${host}`);
}

function firstHeaderValue(value: string | null) {
  return value?.split(",")[0]?.trim() || null;
}

function normalizeOrigin(value: string | null | undefined) {
  if (!value) {
    return null;
  }

  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}
