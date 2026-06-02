# Dynamic Calendar User Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the logged-in Microsoft/Teams user become the platform calendar user consumed dynamically by the .NET bot, without breaking the current `DEV_USER_ID` based development flow.

**Architecture:** Add auth-backed user resolution beside the existing dev-user fallback, then move product APIs to use a `CurrentUser` dependency. Microsoft onboarding upserts `profiles`, `calendar_connections`, and `meeting_settings`; the existing `bot_calendar_users` view then exposes enabled users to the .NET bot. Roll out behind feature flags so current dashboard, meetings, tasks, approvals, and bot reporting continue working while the dynamic path is validated.

**Tech Stack:** Next.js 16, Supabase Auth, FastAPI, Supabase REST service-role gateway, pytest, .NET Teams media bot, Microsoft Graph application permissions.

---

## Compatibility Strategy

Keep the current system working throughout implementation:

- `DEV_USER_ID` remains supported when no frontend bearer token is provided.
- New auth-backed APIs are introduced first, then existing services are migrated one at a time.
- The existing `/internal/bot/calendar-users` contract remains unchanged.
- The .NET bot continues to support its existing configured calendar user until dynamic platform users are confirmed.
- The `bot_calendar_users` view remains the source of truth for bot calendar users.

## File Structure

- Modify: `productivity-platform/backend/app/core/config.py`
  - Add flags for auth rollout and Microsoft OAuth/calendar behavior.
- Create: `productivity-platform/backend/app/auth/current_user.py`
  - Verify Supabase JWT and provide `CurrentUser`.
- Test: `productivity-platform/backend/tests/test_current_user.py`
  - Cover bearer-token success, dev fallback, and auth-required errors.
- Create: `productivity-platform/backend/app/services/user_bootstrap.py`
  - Upsert profile, calendar connection, and default meeting settings for a logged-in user.
- Test: `productivity-platform/backend/tests/test_user_bootstrap.py`
  - Verify idempotent upserts and default settings.
- Modify: `productivity-platform/backend/app/services/meeting_settings.py`
  - Replace direct `get_dev_user_id()` use with injectable user id helpers while preserving fallback.
- Modify gradually: dashboard, meetings, tasks, approvals, meeting chat services.
  - Use current user id instead of global dev user id.
- Modify: `productivity-platform/frontend/components/auth-form.tsx`
  - Add Microsoft sign-in entry point while keeping email/password until cutover.
- Modify: `productivity-platform/frontend/lib/api.ts`
  - Attach Supabase access token to FastAPI calls.
- Modify: `productivity-platform/frontend/app/onboarding/page.tsx`
  - Make Microsoft calendar connection a real action.
- Create: `productivity-platform/backend/supabase/008_auth_bootstrap_policies.sql`
  - Add any missing insert/upsert policies or helper SQL needed for profile/bootstrap.
- Modify external repo: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot`
  - Keep current config fallback, add polling of `/internal/bot/calendar-users`.

---

### Task 1: Backend Current User Dependency

**Files:**
- Create: `productivity-platform/backend/app/auth/current_user.py`
- Modify: `productivity-platform/backend/app/core/config.py`
- Test: `productivity-platform/backend/tests/test_current_user.py`

- [ ] **Step 1: Add tests for auth-backed user resolution**

Create tests that verify:

```python
def test_current_user_uses_dev_user_when_no_bearer_token_and_fallback_enabled():
    assert resolved.user_id == "dev-user-id"

def test_current_user_rejects_missing_token_when_auth_required():
    assert response.status_code == 401

def test_current_user_accepts_valid_supabase_jwt():
    assert resolved.user_id == "auth-user-id"
```

- [ ] **Step 2: Implement `CurrentUser`**

`CurrentUser` should expose:

```python
class CurrentUser(BaseModel):
    user_id: str
    email: str | None = None
    auth_source: Literal["supabase", "dev"]
```

The dependency should:

```text
1. Read Authorization: Bearer <token>.
2. Verify the Supabase JWT using SUPABASE_JWT_SECRET.
3. Return auth.uid/sub as user_id.
4. If no token exists and DEV_USER_ID fallback is enabled, return DEV_USER_ID.
5. Otherwise return 401.
```

- [ ] **Step 3: Run backend tests**

Run:

```powershell
cd productivity-platform\backend
pytest tests/test_current_user.py -v
```

Expected: all tests pass.

---

### Task 2: User Bootstrap Service

**Files:**
- Create: `productivity-platform/backend/app/services/user_bootstrap.py`
- Test: `productivity-platform/backend/tests/test_user_bootstrap.py`

- [ ] **Step 1: Test idempotent bootstrap**

Cover that one call upserts:

```text
profiles.id = current_user.user_id
profiles.email = current_user.email
meeting_settings.user_id = current_user.user_id
calendar_connections.user_id = current_user.user_id
calendar_connections.provider = microsoft
```

- [ ] **Step 2: Implement bootstrap**

Add a service function:

```python
async def ensure_user_workspace(
    user_id: str,
    email: str | None,
    tenant_id: str | None = None,
    aad_user_id: str | None = None,
) -> dict[str, str]:
    ...
```

It should use `supabase_gateway.upsert()` and must be safe to call repeatedly.

- [ ] **Step 3: Keep auto-join conservative**

Default `meeting_settings.auto_join_enabled` should stay `false` unless the user explicitly enables the assistant or onboarding asks for it. This avoids suddenly sending the bot to meetings for existing users.

---

### Task 3: Authenticated API Requests From Frontend

**Files:**
- Modify: `productivity-platform/frontend/lib/api.ts`
- Test manually through browser/network tab.

- [ ] **Step 1: Add token-aware fetch helper**

Create a helper that gets the Supabase session and adds:

```http
Authorization: Bearer <access_token>
```

Use it for product APIs, while allowing server-rendered pages to continue working during fallback.

- [ ] **Step 2: Migrate settings API first**

Start with:

```text
GET /api/v1/settings/meeting-assistant
PUT /api/v1/settings/meeting-assistant
```

This is the lowest-risk user-owned endpoint and directly controls calendar assistant visibility.

- [ ] **Step 3: Verify fallback**

Run frontend without a Supabase token and confirm backend still resolves `DEV_USER_ID` while fallback is enabled.

---

### Task 4: Migrate Backend Product Services Incrementally

**Files:**
- Modify: `productivity-platform/backend/app/api/v1/routes/settings.py`
- Modify: `productivity-platform/backend/app/services/meeting_settings.py`
- Then migrate:
  - `dashboard.py`
  - `meetings.py`
  - `tasks.py`
  - `approvals.py`
  - `meeting_chat.py`

- [ ] **Step 1: Change route layer to accept `CurrentUser`**

Routes should pass `current_user.user_id` into services instead of services calling `get_dev_user_id()` internally.

- [ ] **Step 2: Keep service signatures explicit**

Use:

```python
async def get_meeting_assistant_settings(user_id: str) -> MeetingAssistantSettings:
    ...
```

Do not read global auth state inside service functions.

- [ ] **Step 3: Migrate one service at a time**

After each service migration, run its focused tests. This keeps regressions small and easy to isolate.

---

### Task 5: Microsoft Login and Onboarding

**Files:**
- Modify: `productivity-platform/frontend/components/auth-form.tsx`
- Modify: `productivity-platform/frontend/app/onboarding/page.tsx`
- Add backend route if needed: `productivity-platform/backend/app/api/v1/routes/onboarding.py`

- [ ] **Step 1: Add Microsoft sign-in**

Use Supabase OAuth:

```ts
await supabaseBrowserClient.auth.signInWithOAuth({
  provider: "azure",
  options: {
    redirectTo: `${window.location.origin}/onboarding`,
    scopes: "openid profile email offline_access User.Read",
  },
});
```

- [ ] **Step 2: Bootstrap after OAuth callback**

When onboarding loads with a valid session, call the backend bootstrap endpoint. Store:

```text
Supabase user id
email
tenant_id if available
aad_user_id if available
```

- [ ] **Step 3: Make calendar assistant opt-in**

Onboarding should show an explicit enable action before setting:

```text
meeting_settings.auto_join_enabled = true
calendar_connections.enabled = true
```

---

### Task 6: Preserve and Validate Bot Calendar Contract

**Files:**
- Modify only if needed: `productivity-platform/backend/app/services/bot_calendar_users.py`
- Test: `productivity-platform/backend/tests/test_bot_calendar_users.py`

- [ ] **Step 1: Add tests for dynamic user visibility**

Verify a user appears in `/internal/bot/calendar-users` only when:

```text
calendar_connections.provider = microsoft
calendar_connections.enabled = true
meeting_settings.auto_join_enabled = true
```

- [ ] **Step 2: Keep response shape unchanged**

The .NET bot should still receive:

```json
{
  "user_id": "uuid",
  "tenant_id": "tenant-id",
  "aad_user_id": "aad-user-id",
  "email": "user@company.com",
  "auto_join_enabled": true,
  "require_approval": true
}
```

---

### Task 7: .NET Bot Dynamic Calendar Users

**Files:**
- Modify external repo: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot`

- [ ] **Step 1: Add platform calendar user client**

Create a small client that calls:

```http
GET {PLATFORM_API_BASE_URL}/internal/bot/calendar-users
Authorization: Bearer {BOT_INTERNAL_API_KEY}
```

- [ ] **Step 2: Keep old configured calendar user fallback**

If the platform endpoint is unavailable or returns no users, the bot should continue using the existing configured calendar user. This avoids breaking current local/dev behavior.

- [ ] **Step 3: Scan returned users**

For each returned user, read that user’s calendar using Graph application permissions and report detected meetings back with the same platform `user_id`.

---

### Task 8: Configuration and Security Rollout

**Files:**
- Modify: `productivity-platform/.env.example`
- Modify: `productivity-platform/docs/supabase-setup.md`
- Modify: `productivity-platform/docs/contracts/bot-platform-api.md`

- [ ] **Step 1: Add rollout flags**

Document:

```text
AUTH_REQUIRED=false
ALLOW_DEV_USER_FALLBACK=true
ENABLE_MICROSOFT_ONBOARDING=false
```

Initial rollout keeps fallback enabled.

- [ ] **Step 2: Confirm tenant config**

Required admin-granted Graph permissions already exist:

```text
Calendars.Read
User.Read.All
Calls.JoinGroupCall.All
Calls.AccessMedia.All
```

If `/onlineMeetings` APIs are used, configure the cloud communications application access policy.

- [ ] **Step 3: Restrict mailbox/calendar scope before production**

Use Exchange application access controls so `Calendars.Read` is limited to approved/enabled users instead of every mailbox.

---

### Task 9: End-to-End Verification

**Files:**
- Test environment only.

- [ ] **Step 1: Verify old flow**

With no frontend token and fallback enabled:

```text
Dashboard loads with DEV_USER_ID data.
Meeting assistant settings still save.
Bot still works with current configured calendar user.
```

- [ ] **Step 2: Verify new login flow**

With Microsoft OAuth:

```text
User logs in.
Profile is created.
Calendar connection is created.
Meeting settings are created.
User can enable calendar assistant.
```

- [ ] **Step 3: Verify bot dynamic flow**

After enabling calendar assistant:

```text
GET /internal/bot/calendar-users returns the logged-in user.
.NET bot polls platform users.
.NET bot scans that user’s calendar.
Detected meetings are stored with the correct platform user_id.
```

- [ ] **Step 4: Disable fallback only after sign-off**

Set:

```text
AUTH_REQUIRED=true
ALLOW_DEV_USER_FALLBACK=false
ENABLE_MICROSOFT_ONBOARDING=true
```

Only do this after old-flow and new-flow verification pass.

---

## Rollout Order

1. Add backend current-user dependency with fallback.
2. Add user bootstrap service.
3. Attach frontend Supabase tokens to API calls.
4. Migrate one backend service at a time from `DEV_USER_ID` to `CurrentUser`.
5. Add Microsoft onboarding and explicit assistant enablement.
6. Confirm `/internal/bot/calendar-users` shows dynamic users.
7. Add .NET bot platform-user polling with old config fallback.
8. Enable feature flags in staging.
9. Remove fallback only after production validation.

## Self-Review

- Spec coverage: Covers login, onboarding, user/calendar mapping, backend auth, bot dynamic users, permissions, and safe rollout.
- Placeholder scan: No placeholder tasks are required for execution; each task has concrete files and expected behavior.
- Type consistency: `CurrentUser.user_id`, `calendar_connections.user_id`, `meeting_settings.user_id`, and bot `user_id` all refer to the same Supabase auth user id.
- Scope check: This is one multi-system rollout, but it is intentionally phased so each task is independently testable and backward-compatible.
