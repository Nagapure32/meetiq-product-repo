# Login Page Redesign Design

## Goal

Redesign the Aress MeetIQ login page so it feels polished, enterprise-ready, and consistent with the current dashboard theme.

## Approved Direction

Use option A for layout and option C for behavior, revised after visual review to be lighter and more sophisticated:

- Desktop layout: restrained split page with the auth panel on the left and a compact product preview on the right.
- Mobile layout: auth panel first, with only compact reassurance/security cues below it.
- Primary behavior: Microsoft work-account sign-in is the dominant action.
- Secondary behavior: email/password remains available as a quieter fallback for existing users.
- Visual density: keep the split layout but remove bulky dashboard cards, repeated metrics, and hard color blocks.

## Visual System

The redesign must reuse the existing product language: off-white shell background, white panels, compact typography, 8-10px radii, muted gray text, and light panel shadows. Use `#3d35b0` only for the primary action and tiny accents. The page must not become a marketing landing page. It should feel like a calm, sophisticated entry point to a work-focused meeting productivity dashboard.

## Page Layout

`frontend/app/login/page.tsx` owns the page composition.

Desktop uses a two-column grid:

- Left column: workspace access copy, auth form, and a compact reassurance strip.
- Right column: product preview panel showing meeting intelligence output.

The right-side panel is intentionally minimal. It shows:

- One short product statement.
- One small meeting-insight card.
- Two or three subtle trust points.
- No dense dashboard mockup, no metric grid, and no repeated security chips.

Mobile stacks content with the full product preview hidden or reduced so sign-in remains the first task.

## Auth Form

`frontend/components/auth-form.tsx` owns authentication UI and Supabase interactions.

The Microsoft OAuth button appears first and uses clear work-account language: `Continue with Microsoft`. The email/password path is secondary and visually quieter, separated by a compact divider. The form uses semantic HTML, visible labels, stable ids, native submit behavior, `autocomplete`, `aria-invalid`, `aria-describedby`, and role-based alert messaging.

The password field includes a show/hide control using lucide icons. Login auth failures use generic copy to avoid account enumeration. Signup keeps minimum password validation at 6 characters.

## Testable Helpers

`frontend/lib/auth-form-ui.ts` contains small pure helpers for field validation and submit labels. `frontend/lib/auth-form-ui.test.ts` verifies required email, invalid email, password requirements, signup minimum length, and pending/idle labels.

## Verification

Run these checks from `meetiq-platform-repo/frontend`:

- `node --experimental-strip-types lib/auth-form-ui.test.ts`
- `npm run build`

Also perform source checks for the approved direction:

- Desktop grid keeps the auth column first and product preview second.
- Microsoft button appears before email/password.
- Accessibility attributes exist on inputs and alert message.
- Product preview contains meeting statuses, insight/action items, and security cues.
