"use client";

import { Eye, EyeOff } from "lucide-react";
import { useRouter } from "next/navigation";
import { type FormEvent, useState, useTransition } from "react";
import {
  type AuthFieldErrors,
  type AuthMode,
  getAuthSubmitLabel,
  validateAuthFields,
} from "@/lib/auth-form-ui";
import { microsoftOAuthOptions } from "@/lib/microsoft-oauth";
import { supabaseBrowserClient } from "@/lib/supabase/client";

type AuthAction = "email" | "microsoft" | null;

const emailId = "meetiq-auth-email";
const passwordId = "meetiq-auth-password";
const emailErrorId = "meetiq-auth-email-error";
const passwordErrorId = "meetiq-auth-password-error";
const messageId = "meetiq-auth-message";
const genericLoginFailure = "We couldn't sign you in. Check your details and try again.";

export function AuthForm() {
  const router = useRouter();
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<AuthFieldErrors>({});
  const [message, setMessage] = useState<string | null>(null);
  const [authAction, setAuthAction] = useState<AuthAction>(null);
  const [isPending, startTransition] = useTransition();

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    const nextFieldErrors = validateAuthFields(email, password, mode);
    setFieldErrors(nextFieldErrors);
    if (Object.keys(nextFieldErrors).length > 0) {
      return;
    }

    setAuthAction("email");
    startTransition(async () => {
      try {
        const result =
          mode === "login"
            ? await supabaseBrowserClient.auth.signInWithPassword({ email: email.trim(), password })
            : await supabaseBrowserClient.auth.signUp({
                email: email.trim(),
                password,
                options: {
                  emailRedirectTo: `${window.location.origin}/login`,
                },
              });

        if (result.error) {
          setMessage(mode === "login" ? genericLoginFailure : result.error.message);
          return;
        }

        if (mode === "signup" && !result.data.session) {
          setMessage("Account created. Check your email to confirm your account.");
          return;
        }

        router.push("/");
        router.refresh();
      } finally {
        setAuthAction(null);
      }
    });
  }

  function signInWithMicrosoft() {
    setMessage(null);
    setFieldErrors({});
    setAuthAction("microsoft");
    startTransition(async () => {
      try {
        const { error } = await supabaseBrowserClient.auth.signInWithOAuth({
          provider: "azure",
          options: microsoftOAuthOptions(`${window.location.origin}/onboarding`),
        });

        if (error) {
          setMessage(genericLoginFailure);
        }
      } finally {
        setAuthAction(null);
      }
    });
  }

  function validateEmailField() {
    setFieldErrors((current) => ({
      ...current,
      email: validateAuthFields(email, password, mode).email,
    }));
  }

  function validatePasswordField() {
    setFieldErrors((current) => ({
      ...current,
      password: validateAuthFields(email, password, mode).password,
    }));
  }

  return (
    <div className="mt-6 w-full rounded-[10px] border border-line bg-white p-5 shadow-panel sm:p-6">
      <div className="mb-4">
        <p className="text-sm font-semibold text-ink">Work account</p>
      </div>

      <button
        type="button"
        onClick={signInWithMicrosoft}
        disabled={isPending}
        className="flex h-12 w-full items-center justify-center gap-3 rounded-[10px] bg-brand px-4 text-sm font-semibold text-white shadow-panel transition hover:bg-brand-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <MicrosoftMark />
        <span className="min-w-0 truncate">
          {authAction === "microsoft" && isPending ? "Redirecting..." : "Continue with Microsoft"}
        </span>
      </button>

      <div className="my-5 flex items-center gap-3">
        <span className="h-px flex-1 bg-line" />
        <span className="font-mono text-[10px] uppercase text-muted">email</span>
        <span className="h-px flex-1 bg-line" />
      </div>

      <div className="flex rounded-[10px] bg-[#f3f2ee] p-1">
        <button
          type="button"
          onClick={() => {
            setMode("login");
            setFieldErrors({});
            setMessage(null);
          }}
          className={`h-8 flex-1 rounded-[8px] text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 ${
            mode === "login" ? "bg-white text-ink shadow-panel" : "text-muted"
          }`}
          aria-pressed={mode === "login"}
        >
          Log in
        </button>
        <button
          type="button"
          onClick={() => {
            setMode("signup");
            setFieldErrors({});
            setMessage(null);
          }}
          className={`h-8 flex-1 rounded-[8px] text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 ${
            mode === "signup" ? "bg-white text-ink shadow-panel" : "text-muted"
          }`}
          aria-pressed={mode === "signup"}
        >
          Sign up
        </button>
      </div>

      <form className="mt-5 space-y-4" onSubmit={submit} noValidate>
        <label className="block">
          <span className="text-xs font-medium text-ink">Email address</span>
          <input
            id={emailId}
            name="email"
            type="email"
            autoComplete="username"
            value={email}
            onBlur={validateEmailField}
            onChange={(event) => {
              setEmail(event.target.value);
              setFieldErrors((current) => ({ ...current, email: undefined }));
            }}
            aria-invalid={Boolean(fieldErrors.email)}
            aria-describedby={fieldErrors.email ? emailErrorId : undefined}
            className="mt-2 h-10 w-full rounded-[10px] border border-line bg-[#fbfaf7] px-3 text-sm text-ink outline-none transition placeholder:text-[#a8a8a3] focus:border-brand focus:bg-white focus:shadow-[0_0_0_3px_rgba(61,53,176,0.14)]"
            placeholder="you@company.com"
          />
          {fieldErrors.email ? (
            <span id={emailErrorId} className="mt-1.5 block text-xs leading-5 text-[#8a3300]">
              {fieldErrors.email}
            </span>
          ) : null}
        </label>
        <label className="block">
          <span className="text-xs font-medium text-ink">Password</span>
          <div className="relative mt-2">
            <input
              id={passwordId}
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              value={password}
              onBlur={validatePasswordField}
              onChange={(event) => {
                setPassword(event.target.value);
                setFieldErrors((current) => ({ ...current, password: undefined }));
              }}
              aria-invalid={Boolean(fieldErrors.password)}
              aria-describedby={fieldErrors.password ? passwordErrorId : undefined}
              className="h-10 w-full rounded-[10px] border border-line bg-[#fbfaf7] px-3 pr-11 text-sm text-ink outline-none transition placeholder:text-[#a8a8a3] focus:border-brand focus:bg-white focus:shadow-[0_0_0_3px_rgba(61,53,176,0.14)]"
              placeholder={mode === "login" ? "Your password" : "Minimum 6 characters"}
            />
            <button
              type="button"
              onClick={() => setShowPassword((current) => !current)}
              className="absolute right-1 top-1 grid size-8 place-items-center rounded-[8px] text-muted transition hover:bg-white hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
              aria-label={showPassword ? "Hide password" : "Show password"}
              aria-pressed={showPassword}
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          {fieldErrors.password ? (
            <span id={passwordErrorId} className="mt-1.5 block text-xs leading-5 text-[#8a3300]">
              {fieldErrors.password}
            </span>
          ) : null}
        </label>

        {message ? (
          <p
            id={messageId}
            className="rounded-[10px] border border-[#ead8ad] bg-[#fff8e8] p-3 text-xs leading-5 text-[#7a4d00]"
            role="alert"
          >
            {message}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={isPending}
          aria-describedby={message ? messageId : undefined}
          className="h-10 w-full rounded-[10px] border border-line bg-white text-sm font-medium text-ink transition hover:border-brand hover:bg-[#faf9f5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {getAuthSubmitLabel(mode, authAction === "email" && isPending)}
        </button>
      </form>
    </div>
  );
}

function MicrosoftMark() {
  return (
    <span className="grid size-4 shrink-0 grid-cols-2 gap-0.5" aria-hidden="true">
      <span className="bg-[#f25022]" />
      <span className="bg-[#7fba00]" />
      <span className="bg-[#00a4ef]" />
      <span className="bg-[#ffb900]" />
    </span>
  );
}
