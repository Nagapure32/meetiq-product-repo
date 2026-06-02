"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { microsoftOAuthOptions } from "@/lib/microsoft-oauth";
import { supabaseBrowserClient } from "@/lib/supabase/client";

type Mode = "login" | "signup";

export function AuthForm() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function submit() {
    setMessage(null);
    startTransition(async () => {
      const result =
        mode === "login"
          ? await supabaseBrowserClient.auth.signInWithPassword({ email, password })
          : await supabaseBrowserClient.auth.signUp({
              email,
              password,
              options: {
                emailRedirectTo: `${window.location.origin}/login`,
              },
            });

      if (result.error) {
        setMessage(result.error.message);
        return;
      }

      if (mode === "signup" && !result.data.session) {
        setMessage("Account created. Check your email to confirm your account.");
        return;
      }

      router.push("/");
      router.refresh();
    });
  }

  function signInWithMicrosoft() {
    setMessage(null);
    startTransition(async () => {
      const { error } = await supabaseBrowserClient.auth.signInWithOAuth({
        provider: "azure",
        options: microsoftOAuthOptions(`${window.location.origin}/onboarding`),
      });

      if (error) {
        setMessage(error.message);
      }
    });
  }

  return (
    <div className="w-full max-w-[420px] rounded-[16px] border border-line bg-white p-6 shadow-panel">
      <div className="flex rounded-[10px] bg-[#efefeb] p-1">
        <button
          type="button"
          onClick={() => setMode("login")}
          className={`h-8 flex-1 rounded-[8px] text-xs font-medium ${
            mode === "login" ? "bg-white text-ink shadow-panel" : "text-muted"
          }`}
        >
          Log in
        </button>
        <button
          type="button"
          onClick={() => setMode("signup")}
          className={`h-8 flex-1 rounded-[8px] text-xs font-medium ${
            mode === "signup" ? "bg-white text-ink shadow-panel" : "text-muted"
          }`}
        >
          Sign up
        </button>
      </div>

      <div className="mt-6 space-y-4">
        <label className="block">
          <span className="text-xs font-medium text-ink">Email</span>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="mt-2 h-10 w-full rounded-[10px] border border-line bg-[#faf9f5] px-3 text-sm outline-none"
            placeholder="you@company.com"
          />
        </label>
        <label className="block">
          <span className="text-xs font-medium text-ink">Password</span>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-2 h-10 w-full rounded-[10px] border border-line bg-[#faf9f5] px-3 text-sm outline-none"
            placeholder="Minimum 6 characters"
          />
        </label>
      </div>

      {message ? <p className="mt-4 text-xs leading-5 text-[#8a5d00]">{message}</p> : null}

      <button
        type="button"
        onClick={submit}
        disabled={isPending || !email || !password}
        className="mt-6 h-10 w-full rounded-[10px] bg-brand text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isPending ? "Working..." : mode === "login" ? "Log in" : "Create account"}
      </button>

      <button
        type="button"
        onClick={signInWithMicrosoft}
        disabled={isPending}
        className="mt-3 h-10 w-full rounded-[10px] border border-line bg-white text-sm font-medium text-ink disabled:cursor-not-allowed disabled:opacity-50"
      >
        Continue with Microsoft
      </button>
    </div>
  );
}
