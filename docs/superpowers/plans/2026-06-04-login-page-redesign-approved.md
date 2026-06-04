# Login Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Aress MeetIQ login page with a minimal, sophisticated split layout and Microsoft work-account sign-in as the dominant action.

**Architecture:** Keep page composition in `frontend/app/login/page.tsx`, authentication behavior in `frontend/components/auth-form.tsx`, and pure UI helpers in `frontend/lib/auth-form-ui.ts`. Preserve existing Supabase auth behavior while improving accessibility, validation, and visual hierarchy.

**Tech Stack:** Next.js app router, React client components, Tailwind CSS, Supabase auth, lucide-react, Node TypeScript script tests.

---

### Task 1: Auth UI Helpers

**Files:**
- Create: `frontend/lib/auth-form-ui.ts`
- Create: `frontend/lib/auth-form-ui.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/lib/auth-form-ui.test.ts`:

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

Run from `frontend`:

```bash
node --experimental-strip-types lib/auth-form-ui.test.ts
```

Expected: fail because `auth-form-ui.ts` does not exist.

- [ ] **Step 3: Implement helpers**

Create `frontend/lib/auth-form-ui.ts`:

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

Run from `frontend`:

```bash
node --experimental-strip-types lib/auth-form-ui.test.ts
```

Expected: exit code 0.

### Task 2: Login Page Layout

**Files:**
- Modify: `frontend/app/login/page.tsx`

- [ ] **Step 1: Redesign layout**

Use a mobile-first split layout:

```tsx
<main className="grid min-h-screen bg-shell lg:grid-cols-[minmax(420px,480px)_minmax(0,1fr)]">
```

Left column contains workspace access copy and `<AuthForm />`. Right column contains a soft, minimal product statement with one small insight card and subtle trust points. Avoid a dense dashboard preview, metric grid, and repeated chips.

- [ ] **Step 2: Source check**

Check for:

```text
lg:grid-cols-[minmax(420px,480px)_minmax(0,1fr)]
Continue with Microsoft
Today's meetings
Decision captured
SSO ready
Encrypted transcripts
Admin-controlled sharing
```

### Task 3: Auth Form UX

**Files:**
- Modify: `frontend/components/auth-form.tsx`

- [ ] **Step 1: Convert to accessible semantic form**

Use a real `<form>`, stable `id`, `name`, `autoComplete`, `aria-invalid`, `aria-describedby`, submit-level alert region, and generic login failure copy.

- [ ] **Step 2: Make Microsoft dominant**

Place `Continue with Microsoft` before email/password. Use a quiet divider and render email/password as secondary fallback. Keep existing Supabase email/password and Microsoft OAuth behavior.

- [ ] **Step 3: Add show/hide password**

Use lucide `Eye` and `EyeOff` icons in a real button with `aria-label` and `aria-pressed`.

- [ ] **Step 4: Verify**

Run:

```bash
node --experimental-strip-types lib/auth-form-ui.test.ts
npm run build
```

Expected: both commands exit 0.

### Task 4: Commit and Push

**Files:**
- Stage only files changed for this redesign.

- [ ] **Step 1: Commit**

Run from `meetiq-platform-repo`:

```bash
git add docs/superpowers/specs/2026-06-04-login-page-redesign-design.md docs/superpowers/plans/2026-06-04-login-page-redesign-approved.md frontend/app/login/page.tsx frontend/components/auth-form.tsx frontend/lib/auth-form-ui.ts frontend/lib/auth-form-ui.test.ts
git commit -m "Redesign login page"
```

- [ ] **Step 2: Push**

Run:

```bash
git push origin main
```
