import {
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
  validateAuthFields("user@example.com", "12345", "signup").password === "Use at least 6 characters.",
  "Signup password should show minimum length.",
);
assert(
  Object.keys(validateAuthFields("user@example.com", "secret1", "signup")).length === 0,
  "Valid signup fields should pass.",
);
assert(getAuthSubmitLabel("login", false) === "Log in", "Idle login label should be stable.");
assert(getAuthSubmitLabel("login", true) === "Signing in...", "Pending login label should be specific.");
assert(getAuthSubmitLabel("signup", true) === "Creating account...", "Pending signup label should be specific.");
