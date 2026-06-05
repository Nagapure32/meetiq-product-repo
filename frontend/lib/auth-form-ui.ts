export type AuthMode = "login" | "signup";

export type AuthFieldErrors = {
  email?: string;
  password?: string;
};

export function validateAuthFields(email: string, password: string, mode: AuthMode): AuthFieldErrors {
  const errors: AuthFieldErrors = {};
  const normalizedEmail = email.trim();

  if (!normalizedEmail) {
    errors.email = "Email is required.";
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
    errors.email = "Enter a valid email address.";
  }

  if (!password) {
    errors.password = "Password is required.";
  } else if (mode === "signup" && password.length < 6) {
    errors.password = "Use at least 6 characters.";
  }

  return errors;
}

export function getAuthSubmitLabel(mode: AuthMode, isPending: boolean) {
  if (!isPending) {
    return mode === "login" ? "Log in" : "Create account";
  }

  return mode === "login" ? "Signing in..." : "Creating account...";
}

export function getAuthFailureMessage(mode: AuthMode) {
  return mode === "login"
    ? "We couldn't sign you in. Check your details and try again."
    : "We couldn't create your account. Check your details and try again.";
}
