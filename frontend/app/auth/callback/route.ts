import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";
import { buildAuthRedirectUrl, safeNextPath } from "@/lib/auth-callback";

export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get("code");
  const nextPath = safeNextPath(requestUrl.searchParams.get("next"));
  const publicSiteUrl =
    process.env.NEXT_PUBLIC_SITE_URL ??
    process.env.NEXT_PUBLIC_FRONTEND_BASE_URL ??
    process.env.FRONTEND_BASE_URL;
  const redirectUrl = buildAuthRedirectUrl({
    fallbackOrigin: request.nextUrl.origin,
    headers: request.headers,
    nextPath: code ? nextPath : "/login",
    publicSiteUrl,
  });

  let response = NextResponse.redirect(redirectUrl);
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!code || !supabaseUrl || !supabaseAnonKey) {
    return response;
  }

  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value, options }) => {
          response.cookies.set(name, value, options);
        });
      },
    },
  });

  const { error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) {
    const loginUrl = buildAuthRedirectUrl({
      fallbackOrigin: request.nextUrl.origin,
      headers: request.headers,
      nextPath: "/login",
      publicSiteUrl,
    });
    return NextResponse.redirect(loginUrl);
  }

  return response;
}
