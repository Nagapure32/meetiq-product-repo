export type AuthMode = "login" | "signup";

export type AuthFieldErrors = {
  email?: string;
  password?: string;
};

const signupPasswordMessage = "Use at least 8 characters with uppercase, lowercase, and a number.";

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
  } else if (mode === "signup" && !isValidSignupPassword(password)) {
    errors.password = signupPasswordMessage;
  }

  return errors;
}

function isValidSignupPassword(password: string) {
  return password.length >= 8 && /[a-z]/.test(password) && /[A-Z]/.test(password) && /\d/.test(password);
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
