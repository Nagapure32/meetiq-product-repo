# Supabase Setup

Use this guide to prepare the Supabase project for the MeetIQ platform.

## 1. Create Project

Create a Supabase project and keep these values ready:

```text
Project URL
Anon public key
Service role key
JWT secret
Database connection string
```

## 2. Fill `.env`

Add the values to:

```text
productivity-platform/.env
```

Required variables:

```text
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
DATABASE_URL=
BOT_INTERNAL_API_KEY=
AUTH_REQUIRED=false
ALLOW_DEV_USER_FALLBACK=true
ENABLE_MICROSOFT_ONBOARDING=false
```

Generate `BOT_INTERNAL_API_KEY` as a long random value. This key will also be configured later in the `.NET` bot repo.

## 3. Run Initial SQL

Open Supabase SQL Editor and run:

```text
backend/supabase/001_initial_schema.sql
backend/supabase/008_auth_bootstrap_policies.sql
```

This creates:

```text
profiles
organizations
organization_members
calendar_connections
meeting_settings
meetings
meeting_approvals
transcript_segments
meeting_summaries
action_items
tasks
ai_chat_messages
bot_events
bot_heartbeats
bot_calendar_users view
```

## 4. Test Data For Bot Endpoint

After creating a user through Supabase Auth, insert a matching profile, calendar connection, and meeting settings row.

Example:

```sql
insert into public.profiles (id, email, display_name, timezone)
values (
  'AUTH_USER_UUID_HERE',
  'person@company.com',
  'Person Name',
  'Asia/Kolkata'
);

insert into public.calendar_connections (
  user_id,
  provider,
  tenant_id,
  aad_user_id,
  email,
  enabled,
  connection_status
)
values (
  'AUTH_USER_UUID_HERE',
  'microsoft',
  'MICROSOFT_TENANT_ID',
  'AAD_USER_ID_OR_NULL',
  'person@company.com',
  true,
  'connected'
);

insert into public.meeting_settings (
  user_id,
  auto_join_enabled,
  require_approval,
  approval_lead_minutes,
  look_ahead_minutes,
  join_early_seconds,
  max_late_join_minutes,
  leave_grace_minutes
)
values (
  '2329ecad-17ce-49f7-bf48-c7d3cc15d478
  true,
  true,
  2,
  15,
  0,
  10,
  2
);
```

Then this FastAPI endpoint should return that user:

```text
GET /internal/bot/calendar-users
```

with:

```http
Authorization: Bearer <BOT_INTERNAL_API_KEY>
```

## 5. Dynamic Microsoft Calendar Users

For dynamic login-to-calendar mapping, users sign in with Microsoft through Supabase Auth.
After login, the platform calls:

```text
POST /api/v1/onboarding/bootstrap
Authorization: Bearer <SUPABASE_ACCESS_TOKEN>
```

The backend upserts:

```text
profiles.id = auth user id
calendar_connections.user_id = auth user id
meeting_settings.user_id = auth user id
```

Keep `AUTH_REQUIRED=false` and `ALLOW_DEV_USER_FALLBACK=true` until the new flow is
verified. After verification, set `AUTH_REQUIRED=true` and `ALLOW_DEV_USER_FALLBACK=false`.
