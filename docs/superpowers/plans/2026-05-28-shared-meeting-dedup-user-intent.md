# Shared Meeting Dedup User Intent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow many connected calendar users to request MeetIQ for the same Teams meeting, while guaranteeing only one bot joins that real meeting.

**Architecture:** Introduce a stable meeting dedupe key derived primarily from the Teams join URL. The .NET bot continues scanning every enabled calendar user, but groups duplicate calendar events into one shared meeting candidate before approval/join. Each connected user keeps independent intent (`pending`, `approved`, `rejected`, `expired`), and the bot joins once when at least one eligible intent is approved.

**Tech Stack:** .NET Teams media bot, FastAPI, Supabase SQL, Microsoft Graph calendar events, pytest/smoke tests.

---

## Product Rule

For a meeting with many participants:

```text
Many connected users may have the same Teams meeting on their calendar.
Each connected user can approve or reject for their own workspace.
Only one bot may join the real Teams meeting.
If any connected user approves and no global policy blocks the meeting, the bot joins once.
Users who reject do not receive the transcript/summary/tasks in their workspace.
```

This preserves user autonomy without creating duplicate bot joins.

## Safety Strategy

Do not replace the current flow in one jump.

- Phase 1 deduplicates in memory inside the .NET bot only.
- Phase 2 reports dedupe metadata to FastAPI without changing existing API fields.
- Phase 3 adds database tables/columns for durable shared meeting identity and user intent.
- Existing `meetings`, `meeting_approvals`, transcripts, summaries, and tasks keep working.
- If no dedupe key is found, the bot falls back to the current `CalendarUserId:EventId` key.

---

## File Structure

### Platform Repo

- Create: `productivity-platform/backend/supabase/009_shared_meeting_dedupe.sql`
  - Adds shared meeting instance and per-user intent schema.
- Modify: `productivity-platform/backend/supabase/001_initial_schema.sql`
  - Optional only after migration is validated; do not edit in first pass.
- Modify: `productivity-platform/backend/app/internal/schemas.py`
  - Accept optional `dedupe_key`, `join_url_hash`, and approval/intents metadata from bot.
- Modify: `productivity-platform/backend/app/services/bot_reporting.py`
  - Store dedupe metadata while keeping current meeting upsert behavior.
- Modify: `productivity-platform/backend/app/services/approvals.py`
  - Later phase: expose per-user approval intent status.
- Test: `productivity-platform/backend/tests/test_bot_reporting_shared_meetings.py`

### .NET Bot Repo

- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\CalendarMeetingCandidate.cs` or equivalent model file.
  - Add `DedupeKey`.
- Create: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\TeamsMeetingDedupeKey.cs`
  - Normalizes Teams join URLs and produces deterministic keys.
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\CalendarMeetingService.cs`
  - Fill `DedupeKey` for each candidate.
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\CalendarAutoJoinService.cs`
  - Group candidates by dedupe key; create one join candidate with many user intents.
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\MeetingApprovalModels.cs`
  - Add `DedupeKey`, `PlatformUserId`, and `CalendarUserEmail`.
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\MeetingApprovalStore.cs`
  - Track approvals by dedupe key and user intent, not only calendar event id.
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\EmailApprovalSender.cs`
  - Send email to `CalendarUserEmail`, fallback to `CalendarUserId`, fallback to configured recipient.
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\PlatformBotReportingClient.cs`
  - Send dedupe key to backend when upserting meetings/events.
- Test: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Tests\BotIdentitySmokeTests\Program.cs`
  - Add smoke tests for dedupe and per-user approval behavior.

---

### Task 1: Add Dedupe Key Utility In .NET Bot

**Files:**
- Create: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\TeamsMeetingDedupeKey.cs`
- Test: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Tests\BotIdentitySmokeTests\Program.cs`

- [ ] **Step 1: Add failing smoke tests**

Add tests:

```csharp
Run("teams meeting dedupe key ignores tracking query parameters", TeamsMeetingDedupeKeyIgnoresTrackingQueryParameters);
Run("teams meeting dedupe key falls back to event identity", TeamsMeetingDedupeKeyFallsBackToEventIdentity);

static void TeamsMeetingDedupeKeyIgnoresTrackingQueryParameters()
{
    var first = TeamsMeetingDedupeKey.FromJoinUrl(
        "https://teams.microsoft.com/l/meetup-join/abc?context=%7B%7D&foo=1",
        "event-a");
    var second = TeamsMeetingDedupeKey.FromJoinUrl(
        "https://teams.microsoft.com/l/meetup-join/abc?foo=2&context=%7B%7D",
        "event-b");

    Assert(first == second, "same Teams join URL path should produce same dedupe key");
}

static void TeamsMeetingDedupeKeyFallsBackToEventIdentity()
{
    var key = TeamsMeetingDedupeKey.FromJoinUrl(null, "event-a");
    Assert(key == "event:event-a", "missing join URL should fall back to event id");
}
```

- [ ] **Step 2: Implement utility**

Create:

```csharp
using System.Security.Cryptography;
using System.Text;

namespace TeamsMediaBot.Bot
{
    public static class TeamsMeetingDedupeKey
    {
        public static string FromJoinUrl(string? joinUrl, string eventId)
        {
            if (Uri.TryCreate(joinUrl, UriKind.Absolute, out var uri))
            {
                var normalized = $"{uri.Scheme.ToLowerInvariant()}://{uri.Host.ToLowerInvariant()}{uri.AbsolutePath.ToLowerInvariant()}";
                return $"teams:{Sha256(normalized)}";
            }

            return $"event:{eventId}";
        }

        private static string Sha256(string value)
        {
            var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(value));
            return Convert.ToHexString(bytes).ToLowerInvariant();
        }
    }
}
```

- [ ] **Step 3: Run smoke tests**

Run from bot repo:

```powershell
dotnet run --project Tests\BotIdentitySmokeTests\BotIdentitySmokeTests.csproj
```

Expected: new tests fail before implementation, pass after implementation.

---

### Task 2: Attach Dedupe Key To Calendar Candidates

**Files:**
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\MeetingJoinModels.cs`
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\CalendarMeetingService.cs`

- [ ] **Step 1: Add model field**

Add to `CalendarMeetingCandidate`:

```csharp
public required string DedupeKey { get; init; }
```

- [ ] **Step 2: Populate field**

In `TryCreateMeetingCandidate`, after `eventId` and `joinUrl` are available:

```csharp
DedupeKey = TeamsMeetingDedupeKey.FromJoinUrl(joinUrl, eventId),
```

- [ ] **Step 3: Verify compile**

Run:

```powershell
dotnet build TeamsMediaBot.csproj
```

Expected: build succeeds.

---

### Task 3: Group Duplicate Meetings Before Approval

**Files:**
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\CalendarAutoJoinService.cs`
- Test: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Tests\BotIdentitySmokeTests\Program.cs`

- [ ] **Step 1: Add behavior test**

Add a source-level smoke test that checks `CalendarAutoJoinService.cs` contains a grouping operation by `DedupeKey` before eligible meetings are selected.

```csharp
Run("calendar auto join groups duplicate meetings by dedupe key", CalendarAutoJoinGroupsDuplicateMeetingsByDedupeKey);

static void CalendarAutoJoinGroupsDuplicateMeetingsByDedupeKey()
{
    var source = File.ReadAllText(Path.GetFullPath(Path.Combine(
        AppContext.BaseDirectory,
        "..", "..", "..", "..", "..",
        "Bot",
        "CalendarAutoJoinService.cs")));

    Assert(source.Contains(".GroupBy(item => item.Meeting.DedupeKey", StringComparison.Ordinal),
        "calendar auto join should group meetings by dedupe key");
}
```

- [ ] **Step 2: Implement grouping**

After `meetingsWithUsers` is built, add:

```csharp
var dedupedMeetings = meetingsWithUsers
    .GroupBy(item => item.Meeting.DedupeKey, StringComparer.OrdinalIgnoreCase)
    .Select(SelectMeetingOwner)
    .OrderBy(item => item.Meeting.StartUtc)
    .ToArray();
```

Use `dedupedMeetings` for `_state.UpdateUpcomingMeetings`, eligibility filtering, approval, and join.

- [ ] **Step 3: Add owner selection helper**

```csharp
private static CalendarMeetingWithUser SelectMeetingOwner(IGrouping<string, CalendarMeetingWithUser> group)
{
    return group
        .OrderByDescending(item =>
            string.Equals(item.Meeting.OrganizerEmail, item.CalendarUser.Email, StringComparison.OrdinalIgnoreCase))
        .ThenBy(item => item.Meeting.StartUtc)
        .ThenBy(item => item.CalendarUser.Email, StringComparer.OrdinalIgnoreCase)
        .First();
}
```

If `OrganizerEmail` is not available in `CalendarMeetingCandidate`, add it from Graph event data in Task 2.

- [ ] **Step 4: Track joined/reported by dedupe key**

Replace join/reported keys:

```csharp
private static string GetJoinKey(CalendarMeetingCandidate meeting)
{
    return meeting.DedupeKey;
}
```

This is the important safety change: two users with different Graph event ids but same Teams URL map to one join key.

---

### Task 4: Keep Per-User Approval Intent Separate

**Files:**
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\MeetingApprovalModels.cs`
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\MeetingApprovalStore.cs`
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\MeetingApprovalService.cs`

- [ ] **Step 1: Extend approval model**

Add:

```csharp
public required string DedupeKey { get; init; }
public required string PlatformUserId { get; init; }
public required string CalendarUserEmail { get; init; }
```

- [ ] **Step 2: Change store key**

In `MeetingApprovalStore`, change:

```csharp
var eventKey = CreateEventKey(meeting.CalendarUserId, meeting.EventId);
```

to:

```csharp
var eventKey = CreateIntentKey(meeting.DedupeKey, platformUserId);
```

This means one user can reject while another user can approve the same deduped meeting.

- [ ] **Step 3: Pass platform user identity**

Change `RequestApprovalAsync` signature:

```csharp
public async Task<MeetingApprovalRequest> RequestApprovalAsync(
    PlatformCalendarUser calendarUser,
    CalendarMeetingCandidate meeting,
    DateTimeOffset expiresAtUtc,
    CancellationToken cancellationToken)
```

Then use:

```csharp
approval.PlatformUserId
approval.CalendarUserEmail
```

for notifications and reporting.

- [ ] **Step 4: Any-approved join rule**

In `GetMeetingToJoinAsync`, for each deduped meeting group:

```text
If any intent is approved, return the selected meeting once.
If all known intents are rejected/expired, skip.
If at least one intent is pending, wait.
```

Do not treat one user rejection as a global meeting rejection.

---

### Task 5: Send Approval To Dynamic Calendar User Email

**Files:**
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\EmailApprovalSender.cs`

- [ ] **Step 1: Update recipient selection**

Use:

```csharp
var recipient = !string.IsNullOrWhiteSpace(approval.CalendarUserEmail)
    ? approval.CalendarUserEmail
    : !string.IsNullOrWhiteSpace(approval.CalendarUserId)
        ? approval.CalendarUserId
        : GetConfiguredValue("CalendarAutoJoin:Approval:Email:Recipient");
```

Apply to both Graph and SMTP sender paths.

- [ ] **Step 2: Keep configured recipient as fallback only**

Do not remove `CalendarAutoJoin:Approval:Email:Recipient`. It stays useful for local fallback mode and emergency testing.

---

### Task 6: Report Dedupe Metadata To FastAPI

**Files:**
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\PlatformBotReportingClient.cs`
- Modify: `productivity-platform/backend/app/internal/schemas.py`
- Modify: `productivity-platform/backend/app/services/bot_reporting.py`
- Test: `productivity-platform/backend/tests/test_bot_reporting_service.py`

- [ ] **Step 1: Extend bot payloads with optional fields**

In bot meeting upsert request, include:

```csharp
dedupeKey = meeting.DedupeKey,
calendarUserEmail = calendarUser.Email
```

- [ ] **Step 2: Extend backend schemas**

Add optional fields to the internal meeting upsert schema:

```python
dedupe_key: str | None = None
calendar_user_email: str | None = None
```

- [ ] **Step 3: Store safely**

Initially store these fields in existing `bot_events.payload` and/or new nullable columns from Task 7. Do not make them required yet.

---

### Task 7: Add Durable Shared Meeting Schema

**Files:**
- Create: `productivity-platform/backend/supabase/009_shared_meeting_dedupe.sql`

- [ ] **Step 1: Add shared meeting table**

```sql
create table if not exists public.meeting_instances (
    id uuid primary key default gen_random_uuid(),
    dedupe_key text not null unique,
    join_url text,
    subject text not null,
    organizer_email text,
    start_time timestamptz not null,
    end_time timestamptz not null,
    bot_status text not null default 'not_started',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
```

- [ ] **Step 2: Add per-user intent table**

```sql
create table if not exists public.meeting_user_intents (
    id uuid primary key default gen_random_uuid(),
    meeting_instance_id uuid not null references public.meeting_instances(id) on delete cascade,
    user_id uuid not null references public.profiles(id) on delete cascade,
    meeting_id uuid references public.meetings(id) on delete cascade,
    graph_event_id text not null,
    calendar_email text not null,
    approval_status text not null default 'pending',
    requested_at timestamptz not null default now(),
    decided_at timestamptz,
    decided_via text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (meeting_instance_id, user_id)
);
```

- [ ] **Step 3: Add indexes**

```sql
create index if not exists idx_meeting_instances_start
    on public.meeting_instances(start_time);

create index if not exists idx_meeting_user_intents_user
    on public.meeting_user_intents(user_id, approval_status);
```

- [ ] **Step 4: Add RLS**

```sql
alter table public.meeting_instances enable row level security;
alter table public.meeting_user_intents enable row level security;

create policy "Users can read meeting instances for own intents"
    on public.meeting_instances for select
    using (
        exists (
            select 1
            from public.meeting_user_intents mui
            where mui.meeting_instance_id = id
              and mui.user_id = auth.uid()
        )
    );

create policy "Users can read own meeting intents"
    on public.meeting_user_intents for select
    using (auth.uid() = user_id);
```

Service-role bot writes bypass RLS as today.

---

### Task 8: Backend Upsert Shared Meeting And Intents

**Files:**
- Modify: `productivity-platform/backend/app/services/bot_reporting.py`
- Test: `productivity-platform/backend/tests/test_bot_reporting_service.py`

- [ ] **Step 1: Keep existing meeting upsert**

Do not remove current `meetings` insert/upsert. Existing UI depends on user-owned meetings.

- [ ] **Step 2: Add shared instance upsert**

If `dedupe_key` exists:

```python
instance = await supabase_gateway.upsert(
    "meeting_instances",
    {
        "dedupe_key": payload.dedupe_key,
        "join_url": payload.join_url,
        "subject": payload.subject,
        "organizer_email": payload.organizer_email,
        "start_time": payload.start_time.isoformat(),
        "end_time": payload.end_time.isoformat(),
        "bot_status": payload.bot_status,
    },
    on_conflict="dedupe_key",
)
```

- [ ] **Step 3: Add user intent upsert**

```python
await supabase_gateway.upsert(
    "meeting_user_intents",
    {
        "meeting_instance_id": instance_id,
        "user_id": payload.user_id,
        "meeting_id": meeting_row["id"],
        "graph_event_id": payload.graph_event_id,
        "calendar_email": payload.calendar_user_email or "",
        "approval_status": payload.approval_status,
    },
    on_conflict="meeting_instance_id,user_id",
)
```

- [ ] **Step 4: Tests**

Add tests that two payloads with different `user_id` and `graph_event_id` but same `dedupe_key` create:

```text
1 meeting_instances row
2 meeting_user_intents rows
2 existing meetings rows
```

This preserves current per-user UI while adding shared join control.

---

### Task 9: End-To-End Verification

**Files:**
- No source changes.

- [ ] **Step 1: Verify old single-user flow**

With one calendar user:

```text
One meeting detected.
One approval sent.
One bot joins.
Transcript still appears for that user.
```

- [ ] **Step 2: Verify duplicate meeting flow**

With two connected users invited to same Teams meeting:

```text
Two calendar events detected.
One dedupe group created.
Two user intents created.
Only one bot join attempt happens.
```

- [ ] **Step 3: Verify split approval**

Scenario:

```text
User A rejects.
User B approves.
```

Expected:

```text
Bot joins once for User B.
User A intent remains rejected.
User A does not receive workspace output.
User B receives transcript/summary/tasks.
```

- [ ] **Step 4: Verify all reject**

Scenario:

```text
User A rejects.
User B rejects.
```

Expected:

```text
Bot does not join.
Meeting instance status becomes skipped/not_joined.
No transcript is stored.
```

---

## Rollout Plan

1. Implement in-memory dedupe in the .NET bot.
2. Validate two-user same-meeting case locally.
3. Add backend optional dedupe fields.
4. Add durable `meeting_instances` and `meeting_user_intents`.
5. Update reporting to populate shared meeting/intent tables.
6. Update UI later to show per-user intent state if needed.

## External Work Required From User

You will need to allow editing the external bot repo:

```text
C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot
```

You will also need to run the new SQL migration in Supabase:

```text
productivity-platform/backend/supabase/009_shared_meeting_dedupe.sql
```

Before production, we should test with two real connected users invited to the same Teams meeting.

## Self-Review

- Spec coverage: Covers duplicate calendar events, one bot join, per-user approve/reject intent, privacy visibility, backend durability, and safe rollout.
- Placeholder scan: No `TBD` or vague implementation-only steps remain.
- Type consistency: `dedupe_key` is the shared meeting identity; `meeting_user_intents.user_id` is the platform user; `calendar_email` is the notification/calendar address.
- Scope check: This is intentionally split into bot-first and backend durability phases to avoid breaking current product behavior.
