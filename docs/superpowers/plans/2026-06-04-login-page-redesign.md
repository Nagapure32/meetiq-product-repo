# Login Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Aress MeetIQ login page so it looks more polished while staying consistent with the existing application design.

**Architecture:** Keep the page in `frontend/app/login/page.tsx` and the credential flow in `frontend/components/auth-form.tsx`. Add small pure helpers in `frontend/lib/auth-form-ui.ts` so validation and loading labels are testable without a browser test harness.

**Tech Stack:** Next.js app router, React client component, Tailwind CSS, Supabase auth, Node-based TypeScript script tests.

---

### Task 1: Auth UI Helper Behavior

**Files:**
- Create: `frontend/lib/auth-form-ui.ts`
- Create: `frontend/lib/auth-form-ui.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
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
assert(validateAuthFields("bad-email", "secret1", "login").email === "Enter a valid email address.", "Invalid email should be rejected.");
assert(validateAuthFields("user@example.com", "", "login").password === "Password is required.", "Login password should be required.");
assert(validateAuthFields("user@example.com", "12345", "signup").password === "Use at least 6 characters.", "Signup password should show minimum length.");
assert(Object.keys(validateAuthFields("user@example.com", "secret1", "signup")).length === 0, "Valid signup fields should pass.");
assert(getAuthSubmitLabel("login", false) === "Log in", "Idle login label should be stable.");
assert(getAuthSubmitLabel("login", true) === "Signing in...", "Pending login label should be specific.");
assert(getAuthSubmitLabel("signup", true) === "Creating account...", "Pending signup label should be specific.");
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --experimental-strip-types lib/auth-form-ui.test.ts`
Expected: FAIL because `auth-form-ui.ts` does not exist yet.

- [ ] **Step 3: Implement helpers**

```ts
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --experimental-strip-types lib/auth-form-ui.test.ts`
Expected: PASS with exit code 0.

### Task 2: Login Page Layout

**Files:**
- Modify: `frontend/app/login/page.tsx`

- [ ] **Step 1: Redesign layout**

Use a mobile-first `main` grid with the auth form first on mobile and a brand/product panel on desktop:

```tsx
<main className="grid min-h-screen bg-shell lg:grid-cols-[minmax(0,1fr)_480px]">
```

Keep the existing Aress logo, brand colors, shell background, compact typography, and restrained card styling. Add a product preview panel showing summary, decisions, action items, and Microsoft Teams/calendar cues.

- [ ] **Step 2: Source check**

Run a source check for `lg:grid-cols`, `order-1`, `order-2`, `Aress MeetIQ`, and product preview copy.

### Task 3: Auth Form UX

**Files:**
- Modify: `frontend/components/auth-form.tsx`

- [ ] **Step 1: Convert to accessible form**

Use a real `<form>`, stable `id`, `name`, `autoComplete`, `aria-invalid`, `aria-describedby`, submit-level alert region, and a show/hide password control.

- [ ] **Step 2: Make Microsoft primary**

Place `Continue with Microsoft` above the email/password form, followed by an `or continue with email` divider. Keep email/password tabs and existing Supabase behavior.

- [ ] **Step 3: Verify**

Run helper tests, TypeScript build, and source checks.

### Task 4: Commit and Push

**Files:**
- Stage only files changed for this redesign and plan.

- [ ] **Step 1: Commit**

Run: `git commit -m "Redesign login page"`

- [ ] **Step 2: Push**

Run: `git push origin main`
