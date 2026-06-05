import {
  getAuthFailureMessage,
  getAuthSubmitLabel,
  validateAuthFields,
} from "./auth-form-ui.ts";

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

assert(validateAuthFields("", "", "login").email === "Email is required.", "Empty email should be invalid.");
assert(
  validateAuthFields("bad-email", "secret1", "login").email === "Enter a valid email address.",
  "Invalid email should be rejected.",
);
assert(
  validateAuthFields("user@example.com", "", "login").password === "Password is required.",
  "Login password should be required.",
);
assert(
  validateAuthFields("user@example.com", "Secret1", "signup").password ===
    "Use at least 8 characters with uppercase, lowercase, and a number.",
  "Signup password should require at least 8 characters.",
);
assert(
  validateAuthFields("user@example.com", "password1", "signup").password ===
    "Use at least 8 characters with uppercase, lowercase, and a number.",
  "Signup password should require an uppercase letter.",
);
assert(
  validateAuthFields("user@example.com", "PASSWORD1", "signup").password ===
    "Use at least 8 characters with uppercase, lowercase, and a number.",
  "Signup password should require a lowercase letter.",
);
assert(
  validateAuthFields("user@example.com", "Password", "signup").password ===
    "Use at least 8 characters with uppercase, lowercase, and a number.",
  "Signup password should require a number.",
);
assert(
  Object.keys(validateAuthFields("user@example.com", "Password1", "signup")).length === 0,
  "Valid signup fields should pass.",
);
assert(
  Object.keys(validateAuthFields("user@example.com", "password", "login")).length === 0,
  "Login password should not enforce signup complexity rules.",
);
assert(getAuthSubmitLabel("login", false) === "Log in", "Idle login label should be stable.");
assert(getAuthSubmitLabel("login", true) === "Signing in...", "Pending login label should be specific.");
assert(getAuthSubmitLabel("signup", true) === "Creating account...", "Pending signup label should be specific.");
assert(
  getAuthFailureMessage("login") === "We couldn't sign you in. Check your details and try again.",
  "Login failures should use generic copy.",
);
assert(
  getAuthFailureMessage("signup") === "We couldn't create your account. Check your details and try again.",
  "Signup failures should use generic copy instead of provider errors.",
);
