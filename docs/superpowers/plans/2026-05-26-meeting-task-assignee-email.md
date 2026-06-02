# Meeting Task Assignee Email Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract meeting tasks from transcripts, assign each task to the correct internal tenant user, and send the assignee an SMTP email immediately after the task is created.

**Architecture:** The .NET Teams media bot captures participant identity from Graph call participant callbacks and sends that identity with transcript segments to the FastAPI backend. The backend resolves AI-extracted assignee mentions against transcript speaker identity, meeting participants, calendar attendees, and profiles; it creates tasks only with high-confidence assignee mapping, then sends SMTP email to the resolved assignee. If the assignee cannot be resolved confidently, the task is created as unresolved/unassigned and no email is sent.

**Tech Stack:** ASP.NET Core 8, Microsoft Graph, Bot Framework, Azure Speech, FastAPI, Supabase, Agno/Azure OpenAI, Python `smtplib`, pytest.

---

## Critical Assignment Rules

- Internal tenant users only for v1.
- Never assign by display name alone unless there is exactly one participant/profile match after normalization.
- Prefer stable identifiers in this order: AAD user id, email/UPN, exact participant source id, exact unique display name.
- For first-person phrases such as "I will do it", resolve the assignee to the speaker of the evidence transcript segment.
- If the AI names a person but resolution is ambiguous, create the action item as unresolved and skip SMTP email.
- SMTP email is sent only after the backend creates a task with `assignee_user_id` and an assignee email.

## File Structure

### .NET Bot

- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\ParticipantAudioSourceMapper.cs`
  - Store participant identity fields, not only display name.
- Create: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\GraphUserDirectoryClient.cs`
  - Resolve AAD user ids to email/UPN using current app token and `User.Read.All`.
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\PlatformBotReportingClient.cs`
  - Include speaker identity in transcript segment payloads.
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\CallHandler.cs`
  - Resolve active speaker metadata before reporting transcript segments.
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Controllers\CallsController.cs`
  - Keep callback processing but pass participant payloads through the richer mapper.

### FastAPI Backend

- Modify: `backend/supabase/001_initial_schema.sql`
  - Add participant identity and email notification fields.
- Create: `backend/supabase/006_meeting_task_assignee_email.sql`
  - Migration for existing databases.
- Modify: `backend/app/internal/schemas.py`
  - Accept identity fields on transcript segments.
- Modify: `backend/app/services/bot_reporting.py`
  - Store identity fields in `transcript_segments` and upsert `meeting_participants`.
- Create: `backend/app/services/meeting_participants.py`
  - Read participant directory for a meeting.
- Create: `backend/app/services/assignee_resolution.py`
  - Resolve AI assignee hints to one profile.
- Create: `backend/app/services/task_email.py`
  - Send SMTP task email and record result.
- Modify: `backend/app/services/ai_meetings.py`
  - Ask AI for assignee/evidence fields, resolve assignee, create tasks, trigger email.
- Modify: `backend/app/core/config.py`
  - Add SMTP task notification settings.
- Test: `backend/tests/test_assignee_resolution.py`
- Test: `backend/tests/test_task_email.py`
- Modify: `backend/tests/test_ai_meetings_service.py`

---

## Task 1: Database Contract

**Files:**
- Modify: `backend/supabase/001_initial_schema.sql`
- Create: `backend/supabase/006_meeting_task_assignee_email.sql`

- [ ] **Step 1: Add migration SQL**

Create `backend/supabase/006_meeting_task_assignee_email.sql`:

```sql
create table if not exists public.meeting_participants (
    id uuid primary key default gen_random_uuid(),
    meeting_id uuid not null references public.meetings(id) on delete cascade,
    source_id text,
    participant_id text,
    aad_user_id text,
    display_name text,
    email text,
    user_principal_name text,
    tenant_id text,
    raw_identity jsonb not null default '{}'::jsonb,
    first_seen_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),
    unique (meeting_id, source_id)
);

alter table public.transcript_segments
    add column if not exists speaker_participant_id text,
    add column if not exists speaker_aad_user_id text,
    add column if not exists speaker_email text,
    add column if not exists speaker_user_principal_name text;

alter table public.action_items
    add column if not exists assignee_display_name text,
    add column if not exists assignee_email text,
    add column if not exists assignee_resolution_status text not null default 'unresolved',
    add column if not exists assignee_resolution_confidence numeric,
    add column if not exists assignee_resolution_reason text;

alter table public.tasks
    add column if not exists assignee_email text,
    add column if not exists assignment_source text,
    add column if not exists notification_status text not null default 'not_sent',
    add column if not exists notification_sent_at timestamptz,
    add column if not exists notification_error text;

create index if not exists idx_meeting_participants_meeting
    on public.meeting_participants(meeting_id);

create index if not exists idx_meeting_participants_aad
    on public.meeting_participants(aad_user_id);

create index if not exists idx_transcript_segments_speaker_source
    on public.transcript_segments(meeting_id, source_id);
```

- [ ] **Step 2: Mirror schema in initial SQL**

Add the same `meeting_participants` table and new columns to `backend/supabase/001_initial_schema.sql` so fresh databases match migrated databases.

- [ ] **Step 3: Verify SQL references**

Run:

```powershell
Select-String -Path backend\supabase\*.sql -Pattern "meeting_participants","speaker_aad_user_id","notification_status"
```

Expected: matches in `001_initial_schema.sql` and `006_meeting_task_assignee_email.sql`.

---

## Task 2: Bot Participant Identity Model

**Files:**
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\ParticipantAudioSourceMapper.cs`

- [ ] **Step 1: Add participant identity record**

Replace the existing `ParticipantAudioSource` record with:

```csharp
public sealed record ParticipantAudioSource(
    string SourceId,
    string DisplayName,
    string? ParticipantId,
    string? AadUserId,
    string? TenantId,
    string? Email,
    string? UserPrincipalName,
    bool? IsMuted,
    string RawIdentityJson);
```

- [ ] **Step 2: Extract identity fields from Graph callback JSON**

Inside `UpdateFromParticipants(JArray participants)`, extract:

```csharp
var identity = participantToken["info"]?["identity"];
var user = identity?["user"];
var aadUserId = user?["id"]?.ToString();
var tenantId = user?["tenantId"]?.ToString()
    ?? participantToken["info"]?["tenantId"]?.ToString();
var email = user?["email"]?.ToString();
var upn = user?["userPrincipalName"]?.ToString();
var rawIdentityJson = identity?.ToString(Newtonsoft.Json.Formatting.None) ?? "{}";
```

When constructing `ParticipantAudioSource`, pass these fields:

```csharp
var source = new ParticipantAudioSource(
    sourceId,
    displayName,
    participantId,
    aadUserId,
    tenantId,
    email,
    upn,
    isMuted,
    rawIdentityJson);
```

- [ ] **Step 3: Add lookup API**

Add this method to `ParticipantAudioSourceMapper`:

```csharp
public bool TryResolve(string? sourceId, out ParticipantAudioSource source)
{
    if (!string.IsNullOrWhiteSpace(sourceId) && _sources.TryGetValue(sourceId, out source!))
    {
        return true;
    }

    source = null!;
    return false;
}
```

- [ ] **Step 4: Build .NET bot**

Run:

```powershell
dotnet build
```

Expected: build succeeds.

---

## Task 3: Bot Graph User Email Resolution

**Files:**
- Create: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\GraphUserDirectoryClient.cs`
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Program.cs`
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\CallHandler.cs`

- [ ] **Step 1: Create directory client**

Create `Bot\GraphUserDirectoryClient.cs`:

```csharp
using System.Net.Http.Headers;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json.Linq;

namespace TeamsMediaBot.Bot
{
    public sealed record GraphUserDirectoryEntry(
        string AadUserId,
        string? DisplayName,
        string? Mail,
        string? UserPrincipalName);

    public sealed class GraphUserDirectoryClient
    {
        private readonly IHttpClientFactory _httpClientFactory;
        private readonly GraphAccessTokenProvider _tokenProvider;
        private readonly ILogger<GraphUserDirectoryClient> _logger;

        public GraphUserDirectoryClient(
            IHttpClientFactory httpClientFactory,
            GraphAccessTokenProvider tokenProvider,
            ILogger<GraphUserDirectoryClient> logger)
        {
            _httpClientFactory = httpClientFactory;
            _tokenProvider = tokenProvider;
            _logger = logger;
        }

        public async Task<GraphUserDirectoryEntry?> GetUserAsync(
            string? aadUserId,
            CancellationToken cancellationToken)
        {
            if (string.IsNullOrWhiteSpace(aadUserId))
            {
                return null;
            }

            var token = await _tokenProvider.GetAccessTokenAsync();
            using var httpClient = _httpClientFactory.CreateClient();
            httpClient.DefaultRequestHeaders.Authorization =
                new AuthenticationHeaderValue("Bearer", token);

            var url =
                $"https://graph.microsoft.com/v1.0/users/{Uri.EscapeDataString(aadUserId)}" +
                "?$select=id,displayName,mail,userPrincipalName";

            using var response = await httpClient.GetAsync(url, cancellationToken);
            var body = await response.Content.ReadAsStringAsync(cancellationToken);
            if (!response.IsSuccessStatusCode)
            {
                _logger.LogWarning(
                    "Graph user lookup failed. AadUserId={AadUserId}, StatusCode={StatusCode}, Response={Response}",
                    aadUserId,
                    response.StatusCode,
                    body);
                return null;
            }

            var json = JObject.Parse(body);
            return new GraphUserDirectoryEntry(
                json["id"]?.ToString() ?? aadUserId,
                json["displayName"]?.ToString(),
                json["mail"]?.ToString(),
                json["userPrincipalName"]?.ToString());
        }
    }
}
```

- [ ] **Step 2: Register client**

In `Program.cs`, add:

```csharp
builder.Services.AddSingleton<GraphUserDirectoryClient>();
```

- [ ] **Step 3: Inject client into `CallHandler`**

Add a constructor parameter:

```csharp
GraphUserDirectoryClient graphUserDirectoryClient,
```

Store it in:

```csharp
private readonly GraphUserDirectoryClient _graphUserDirectoryClient;
```

- [ ] **Step 4: Build .NET bot**

Run:

```powershell
dotnet build
```

Expected: build succeeds. If Graph lookup returns `403`, confirm `User.Read.All` has admin consent for application permissions.

---

## Task 4: Send Speaker Identity With Transcript Segments

**Files:**
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\PlatformBotReportingClient.cs`
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\Bot\CallHandler.cs`

- [ ] **Step 1: Extend reporting method signature**

Change `RecordTranscriptSegmentAsync` signature to:

```csharp
public async Task RecordTranscriptSegmentAsync(
    string? platformMeetingId,
    int? sequence,
    DateTimeOffset? timestampUtc,
    string speaker,
    string? sourceId,
    string? participantId,
    string? aadUserId,
    string? speakerEmail,
    string? speakerUserPrincipalName,
    string? language,
    string text,
    CancellationToken cancellationToken)
```

- [ ] **Step 2: Include identity fields in JSON**

Inside the segment payload, add:

```csharp
speakerParticipantId = participantId,
speakerAadUserId = aadUserId,
speakerEmail = speakerEmail,
speakerUserPrincipalName = speakerUserPrincipalName,
```

The full segment object should include:

```csharp
new
{
    sequence,
    speaker,
    sourceId,
    speakerParticipantId = participantId,
    speakerAadUserId = aadUserId,
    speakerEmail,
    speakerUserPrincipalName,
    language,
    text,
    startedAt = transcriptTimestamp,
    endedAt = transcriptTimestamp
}
```

- [ ] **Step 3: Resolve identity in `CallHandler`**

Before calling `RecordTranscriptSegmentAsync`, add:

```csharp
ParticipantAudioSource? participant = null;
_participantAudioSourceMapper.TryResolve(sourceId, out participant!);

var graphUser = participant?.AadUserId == null
    ? null
    : await _graphUserDirectoryClient.GetUserAsync(participant.AadUserId, CancellationToken.None);

var speakerEmail = FirstNonEmpty(participant?.Email, graphUser?.Mail, graphUser?.UserPrincipalName);
var speakerUpn = FirstNonEmpty(participant?.UserPrincipalName, graphUser?.UserPrincipalName);
```

Add helper:

```csharp
private static string? FirstNonEmpty(params string?[] values)
{
    return values.FirstOrDefault(value => !string.IsNullOrWhiteSpace(value));
}
```

- [ ] **Step 4: Pass identity fields**

Update the call:

```csharp
_ = _platformBotReportingClient.RecordTranscriptSegmentAsync(
    context.PlatformMeetingId,
    transcriptEntry?.Sequence,
    transcriptEntry?.TimestampUtc,
    speakerLabel,
    sourceId,
    participant?.ParticipantId,
    participant?.AadUserId,
    speakerEmail,
    speakerUpn,
    detectedLanguage,
    e.Result.Text,
    CancellationToken.None);
```

- [ ] **Step 5: Build .NET bot**

Run:

```powershell
dotnet build
```

Expected: build succeeds.

---

## Task 5: Backend Transcript Identity Ingestion

**Files:**
- Modify: `backend/app/internal/schemas.py`
- Modify: `backend/app/services/bot_reporting.py`
- Create: `backend/app/services/meeting_participants.py`

- [ ] **Step 1: Extend internal transcript schema**

In `BotTranscriptSegment`, add:

```python
speaker_participant_id: str | None = None
speaker_aad_user_id: str | None = None
speaker_email: str | None = None
speaker_user_principal_name: str | None = None
```

- [ ] **Step 2: Store transcript identity fields**

In `record_bot_transcript`, add these keys to each inserted row:

```python
"speaker_participant_id": segment.speaker_participant_id,
"speaker_aad_user_id": segment.speaker_aad_user_id,
"speaker_email": segment.speaker_email,
"speaker_user_principal_name": segment.speaker_user_principal_name,
```

- [ ] **Step 3: Upsert participant rows**

After inserting transcript rows, upsert `meeting_participants` for segments with `source_id`:

```python
participant_payloads = []
for segment in payload.segments:
    if not segment.source_id:
        continue
    participant_payloads.append(
        {
            "meeting_id": payload.meeting_id,
            "source_id": segment.source_id,
            "participant_id": segment.speaker_participant_id,
            "aad_user_id": segment.speaker_aad_user_id,
            "display_name": segment.speaker,
            "email": segment.speaker_email,
            "user_principal_name": segment.speaker_user_principal_name,
            "last_seen_at": datetime.now(UTC).isoformat(),
        }
    )
if participant_payloads:
    for item in participant_payloads:
        await supabase_gateway.upsert(
            "meeting_participants",
            item,
            on_conflict="meeting_id,source_id",
        )
```

- [ ] **Step 4: Add participant reader service**

Create `backend/app/services/meeting_participants.py`:

```python
from typing import Any

from app.db.supabase import supabase_gateway


async def list_meeting_participants(meeting_id: str) -> list[dict[str, Any]]:
    return await supabase_gateway.get(
        "meeting_participants",
        {
            "select": "*",
            "meeting_id": f"eq.{meeting_id}",
        },
    )
```

- [ ] **Step 5: Run backend tests**

Run:

```powershell
python -m pytest backend\tests -q
```

Expected: existing tests pass after updates to fake gateways where needed.

---

## Task 6: Assignee Resolution Service

**Files:**
- Create: `backend/app/services/assignee_resolution.py`
- Create: `backend/tests/test_assignee_resolution.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_assignee_resolution.py`:

```python
from app.services.assignee_resolution import resolve_assignee


def test_resolves_first_person_to_speaker_email():
    result = resolve_assignee(
        assignee_name="I",
        evidence_segment={
            "speaker": "Ravi Sharma",
            "source_id": "7",
            "speaker_email": "ravi@example.com",
            "speaker_aad_user_id": "aad-ravi",
        },
        participants=[
            {
                "source_id": "7",
                "display_name": "Ravi Sharma",
                "email": "ravi@example.com",
                "aad_user_id": "aad-ravi",
            }
        ],
        profiles=[
            {"id": "user-ravi", "display_name": "Ravi Sharma", "email": "ravi@example.com"},
        ],
    )

    assert result.user_id == "user-ravi"
    assert result.email == "ravi@example.com"
    assert result.status == "resolved"
    assert result.confidence == 1.0


def test_resolves_unique_named_participant_to_profile():
    result = resolve_assignee(
        assignee_name="Priya",
        evidence_segment={"speaker": "Asha", "source_id": "3"},
        participants=[
            {"display_name": "Priya Kale", "email": "priya@example.com", "aad_user_id": "aad-priya"},
            {"display_name": "Ravi Sharma", "email": "ravi@example.com", "aad_user_id": "aad-ravi"},
        ],
        profiles=[
            {"id": "user-priya", "display_name": "Priya Kale", "email": "priya@example.com"},
            {"id": "user-ravi", "display_name": "Ravi Sharma", "email": "ravi@example.com"},
        ],
    )

    assert result.user_id == "user-priya"
    assert result.email == "priya@example.com"
    assert result.status == "resolved"


def test_does_not_resolve_ambiguous_display_name():
    result = resolve_assignee(
        assignee_name="Ravi",
        evidence_segment={"speaker": "Asha", "source_id": "3"},
        participants=[
            {"display_name": "Ravi Sharma", "email": "ravi@example.com"},
            {"display_name": "Ravi Kumar", "email": "ravi.kumar@example.com"},
        ],
        profiles=[
            {"id": "user-1", "display_name": "Ravi Sharma", "email": "ravi@example.com"},
            {"id": "user-2", "display_name": "Ravi Kumar", "email": "ravi.kumar@example.com"},
        ],
    )

    assert result.user_id is None
    assert result.email is None
    assert result.status == "unresolved"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest backend\tests\test_assignee_resolution.py -q
```

Expected: FAIL because `app.services.assignee_resolution` does not exist.

- [ ] **Step 3: Implement resolver**

Create `backend/app/services/assignee_resolution.py`:

```python
from dataclasses import dataclass
from typing import Any


FIRST_PERSON = {"i", "me", "myself", "we", "us"}


@dataclass(frozen=True)
class AssigneeResolution:
    user_id: str | None
    email: str | None
    display_name: str | None
    status: str
    confidence: float
    reason: str


def resolve_assignee(
    assignee_name: str | None,
    evidence_segment: dict[str, Any] | None,
    participants: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
) -> AssigneeResolution:
    clean_name = _normalize(assignee_name)
    evidence_segment = evidence_segment or {}

    if clean_name in FIRST_PERSON:
        email = _first_non_empty(
            evidence_segment.get("speaker_email"),
            evidence_segment.get("speaker_user_principal_name"),
        )
        aad_user_id = evidence_segment.get("speaker_aad_user_id")
        return _resolve_by_stable_identity(
            email=email,
            aad_user_id=aad_user_id,
            display_name=evidence_segment.get("speaker"),
            profiles=profiles,
            reason="first_person_speaker",
        )

    if not clean_name:
        return AssigneeResolution(None, None, None, "unresolved", 0.0, "missing_assignee")

    participant_matches = [
        participant
        for participant in participants
        if _name_matches(clean_name, participant.get("display_name"))
    ]
    if len(participant_matches) != 1:
        return AssigneeResolution(None, None, assignee_name, "unresolved", 0.0, "ambiguous_or_missing_participant")

    participant = participant_matches[0]
    return _resolve_by_stable_identity(
        email=_first_non_empty(participant.get("email"), participant.get("user_principal_name")),
        aad_user_id=participant.get("aad_user_id"),
        display_name=participant.get("display_name"),
        profiles=profiles,
        reason="unique_participant_name",
    )


def _resolve_by_stable_identity(
    email: str | None,
    aad_user_id: str | None,
    display_name: str | None,
    profiles: list[dict[str, Any]],
    reason: str,
) -> AssigneeResolution:
    profile = _find_profile_by_email(email, profiles)
    if profile:
        return AssigneeResolution(
            profile.get("id"),
            profile.get("email") or email,
            profile.get("display_name") or display_name,
            "resolved",
            1.0,
            reason,
        )

    if email:
        return AssigneeResolution(None, email, display_name, "email_only", 0.8, reason)

    return AssigneeResolution(None, None, display_name, "unresolved", 0.0, f"{reason}_without_email")


def _find_profile_by_email(email: str | None, profiles: list[dict[str, Any]]) -> dict[str, Any] | None:
    clean_email = _normalize_email(email)
    if not clean_email:
        return None
    for profile in profiles:
        if _normalize_email(profile.get("email")) == clean_email:
            return profile
    return None


def _name_matches(query: str, display_name: str | None) -> bool:
    clean_display = _normalize(display_name)
    if not query or not clean_display:
        return False
    return query == clean_display or query in clean_display.split()


def _normalize(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def _first_non_empty(*values: str | None) -> str | None:
    return next((value for value in values if value and value.strip()), None)
```

- [ ] **Step 4: Run resolver tests**

Run:

```powershell
python -m pytest backend\tests\test_assignee_resolution.py -q
```

Expected: PASS.

---

## Task 7: SMTP Task Notification Service

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/task_email.py`
- Create: `backend/tests/test_task_email.py`

- [ ] **Step 1: Add config fields**

In `Settings` inside `backend/app/core/config.py`, add:

```python
task_email_enabled: bool = Field(default=True, alias="TASK_EMAIL_ENABLED")
task_smtp_host: str = Field(default="", alias="TASK_SMTP_HOST")
task_smtp_port: int = Field(default=587, alias="TASK_SMTP_PORT")
task_smtp_username: str = Field(default="", alias="TASK_SMTP_USERNAME")
task_smtp_password: str = Field(default="", alias="TASK_SMTP_PASSWORD")
task_smtp_from_address: str = Field(default="", alias="TASK_SMTP_FROM_ADDRESS")
task_smtp_from_name: str = Field(default="MeetIQ", alias="TASK_SMTP_FROM_NAME")
task_smtp_enable_tls: bool = Field(default=True, alias="TASK_SMTP_ENABLE_TLS")
```

- [ ] **Step 2: Write failing email tests**

Create `backend/tests/test_task_email.py`:

```python
from app.services import task_email


class FakeSettings:
    task_email_enabled = True
    task_smtp_host = "smtp.example.com"
    task_smtp_port = 587
    task_smtp_username = "sender@example.com"
    task_smtp_password = "secret"
    task_smtp_from_address = "sender@example.com"
    task_smtp_from_name = "MeetIQ"
    task_smtp_enable_tls = True


class FakeSmtp:
    sent_messages = []

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.started_tls = False
        self.logged_in = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def starttls(self):
        self.started_tls = True

    def login(self, username, password):
        self.logged_in = (username, password)

    def send_message(self, message):
        self.sent_messages.append(message)


def test_send_task_email_uses_assignee_email(monkeypatch):
    FakeSmtp.sent_messages = []
    monkeypatch.setattr(task_email, "settings", FakeSettings())
    monkeypatch.setattr(task_email.smtplib, "SMTP", FakeSmtp)

    result = task_email.send_task_assignment_email(
        to_email="ravi@example.com",
        assignee_name="Ravi Sharma",
        task={
            "title": "Send pricing notes",
            "description": "Send pricing notes to the client.",
            "priority": "high",
            "due_date": "2026-05-27",
        },
        meeting={"subject": "Roadmap sync"},
    )

    assert result.sent is True
    assert FakeSmtp.sent_messages[0]["To"] == "ravi@example.com"
    assert "Send pricing notes" in FakeSmtp.sent_messages[0]["Subject"]


def test_send_task_email_skips_without_recipient(monkeypatch):
    monkeypatch.setattr(task_email, "settings", FakeSettings())

    result = task_email.send_task_assignment_email(
        to_email=None,
        assignee_name=None,
        task={"title": "Send pricing notes"},
        meeting={"subject": "Roadmap sync"},
    )

    assert result.sent is False
    assert result.reason == "missing_recipient"
```

- [ ] **Step 3: Implement email service**

Create `backend/app/services/task_email.py`:

```python
from dataclasses import dataclass
from email.message import EmailMessage
import html
import smtplib
from typing import Any

from app.core.config import settings


@dataclass(frozen=True)
class TaskEmailResult:
    sent: bool
    reason: str
    error: str | None = None


def send_task_assignment_email(
    to_email: str | None,
    assignee_name: str | None,
    task: dict[str, Any],
    meeting: dict[str, Any] | None,
) -> TaskEmailResult:
    if not settings.task_email_enabled:
        return TaskEmailResult(False, "disabled")
    if not to_email:
        return TaskEmailResult(False, "missing_recipient")
    if not _smtp_configured():
        return TaskEmailResult(False, "smtp_not_configured")

    message = EmailMessage()
    from_address = settings.task_smtp_from_address or settings.task_smtp_username
    message["From"] = f"{settings.task_smtp_from_name} <{from_address}>"
    message["To"] = to_email
    message["Subject"] = f"New task assigned: {task.get('title')}"
    message.set_content(_plain_body(assignee_name, task, meeting))
    message.add_alternative(_html_body(assignee_name, task, meeting), subtype="html")

    try:
        with smtplib.SMTP(settings.task_smtp_host, settings.task_smtp_port) as smtp:
            if settings.task_smtp_enable_tls:
                smtp.starttls()
            smtp.login(settings.task_smtp_username, settings.task_smtp_password)
            smtp.send_message(message)
    except Exception as exc:
        return TaskEmailResult(False, "smtp_error", str(exc))

    return TaskEmailResult(True, "sent")


def _smtp_configured() -> bool:
    return all(
        [
            settings.task_smtp_host,
            settings.task_smtp_username,
            settings.task_smtp_password,
            settings.task_smtp_from_address or settings.task_smtp_username,
        ]
    )


def _plain_body(assignee_name: str | None, task: dict[str, Any], meeting: dict[str, Any] | None) -> str:
    return (
        f"Hi {assignee_name or 'there'},\n\n"
        f"You have been assigned a task from {meeting_subject(meeting)}.\n\n"
        f"Task: {task.get('title')}\n"
        f"Description: {task.get('description') or 'No description'}\n"
        f"Priority: {task.get('priority') or 'medium'}\n"
        f"Due date: {task.get('due_date') or 'Not set'}\n"
    )


def _html_body(assignee_name: str | None, task: dict[str, Any], meeting: dict[str, Any] | None) -> str:
    return f"""
    <p>Hi {html.escape(assignee_name or 'there')},</p>
    <p>You have been assigned a task from <strong>{html.escape(meeting_subject(meeting))}</strong>.</p>
    <p><strong>Task:</strong> {html.escape(str(task.get('title') or 'Untitled task'))}<br>
    <strong>Description:</strong> {html.escape(str(task.get('description') or 'No description'))}<br>
    <strong>Priority:</strong> {html.escape(str(task.get('priority') or 'medium'))}<br>
    <strong>Due date:</strong> {html.escape(str(task.get('due_date') or 'Not set'))}</p>
    """


def meeting_subject(meeting: dict[str, Any] | None) -> str:
    return str((meeting or {}).get("subject") or "a meeting")
```

- [ ] **Step 4: Run email tests**

Run:

```powershell
python -m pytest backend\tests\test_task_email.py -q
```

Expected: PASS.

---

## Task 8: AI Extraction With Evidence and Assignee Hints

**Files:**
- Modify: `backend/app/services/ai_meetings.py`
- Modify: `backend/tests/test_ai_meetings_service.py`

- [ ] **Step 1: Extend `MeetingAITask`**

Update dataclass:

```python
@dataclass(frozen=True)
class MeetingAITask:
    title: str
    description: str | None = None
    priority: str = "medium"
    due_date: str | None = None
    assignee_name: str | None = None
    evidence_segment_sequence: int | None = None
```

- [ ] **Step 2: Update AI instructions**

Replace task instruction lines with:

```python
"tasks must be an array of objects with title, description, priority, due_date, assignee_name, evidence_segment_sequence.",
"assignee_name must be the person who accepted or was assigned the work. Use I/me when the speaker assigned work to themselves.",
"evidence_segment_sequence must be the transcript segment sequence number that proves the assignment.",
"Do not invent assignees. Use null for assignee_name when the transcript does not say who owns the work.",
```

- [ ] **Step 3: Include sequence in prompt**

Change transcript rendering to:

```python
transcript = "\n".join(
    (
        f"[{segment.get('sequence')}] "
        f"{segment.get('speaker') or 'Unknown speaker'}: {segment.get('text') or ''}"
    )
    for segment in transcript_segments
)
```

- [ ] **Step 4: Parse new fields**

In `_parse_ai_result`, update `MeetingAITask` construction:

```python
MeetingAITask(
    title=str(task.get("title", "")).strip(),
    description=task.get("description"),
    priority=_normalize_priority(task.get("priority")),
    due_date=task.get("due_date"),
    assignee_name=task.get("assignee_name"),
    evidence_segment_sequence=_parse_optional_int(task.get("evidence_segment_sequence")),
)
```

Add:

```python
def _parse_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
```

- [ ] **Step 5: Update tests**

Change existing `MeetingAITask(...)` fixtures in `backend/tests/test_ai_meetings_service.py` to include:

```python
assignee_name="Ravi",
evidence_segment_sequence=1,
```

- [ ] **Step 6: Run AI service tests**

Run:

```powershell
python -m pytest backend\tests\test_ai_meetings_service.py -q
```

Expected: tests pass or fail only because assignment behavior changes in Task 9.

---

## Task 9: Correct Task Assignment and SMTP Trigger

**Files:**
- Modify: `backend/app/services/ai_meetings.py`
- Modify: `backend/tests/test_ai_meetings_service.py`

- [ ] **Step 1: Add fake tables to tests**

In `FakeSupabaseGateway.__init__`, add:

```python
"profiles": [],
"meeting_participants": [],
```

Update `get` to support `in.(...)` filters:

```python
if isinstance(value, str) and value.startswith("in.("):
    expected_values = value[4:-1].split(",")
    rows = [row for row in rows if str(row.get(key)) in expected_values]
```

- [ ] **Step 2: Write assignment test**

Add test:

```python
def test_generate_meeting_intelligence_assigns_named_user_and_sends_email(monkeypatch):
    from app.services import ai_meetings

    fake = FakeSupabaseGateway()
    fake.tables["meetings"] = [{"id": "meeting-1", "user_id": "owner-1", "subject": "Roadmap sync"}]
    fake.tables["transcript_segments"] = [
        {
            "id": "segment-1",
            "sequence": 1,
            "speaker": "Asha",
            "source_id": "source-asha",
            "text": "Ravi will send the pricing notes tomorrow.",
            "created_at": "2026-05-20T10:00:00Z",
        }
    ]
    fake.tables["meeting_participants"] = [
        {
            "meeting_id": "meeting-1",
            "source_id": "source-ravi",
            "display_name": "Ravi Sharma",
            "email": "ravi@example.com",
            "aad_user_id": "aad-ravi",
        }
    ]
    fake.tables["profiles"] = [
        {"id": "user-ravi", "display_name": "Ravi Sharma", "email": "ravi@example.com"}
    ]
    ai_result = ai_meetings.MeetingAIResult(
        summary="Ravi owns pricing follow-up.",
        key_points=[],
        decisions=[],
        tasks=[
            ai_meetings.MeetingAITask(
                title="Send pricing notes",
                description="Send pricing notes to the client.",
                priority="high",
                due_date=None,
                assignee_name="Ravi",
                evidence_segment_sequence=1,
            )
        ],
    )
    sent = []
    monkeypatch.setattr(ai_meetings, "supabase_gateway", fake)
    monkeypatch.setattr(ai_meetings, "_run_agno_meeting_agent", lambda *_: ai_result)
    monkeypatch.setattr(
        ai_meetings,
        "send_task_assignment_email",
        lambda **kwargs: sent.append(kwargs) or ai_meetings.TaskEmailResult(True, "sent"),
    )

    result = run(ai_meetings.generate_meeting_intelligence("meeting-1"))

    assert result["created_tasks_count"] == 1
    assert fake.tables["tasks"][0]["assignee_user_id"] == "user-ravi"
    assert fake.tables["tasks"][0]["assignee_email"] == "ravi@example.com"
    assert fake.tables["task_assignees"][0]["user_id"] == "user-ravi"
    assert fake.tables["tasks"][0]["notification_status"] == "sent"
    assert sent[0]["to_email"] == "ravi@example.com"
```

- [ ] **Step 3: Write ambiguity test**

Add test:

```python
def test_generate_meeting_intelligence_skips_email_when_assignee_ambiguous(monkeypatch):
    from app.services import ai_meetings

    fake = FakeSupabaseGateway()
    fake.tables["meetings"] = [{"id": "meeting-1", "user_id": "owner-1", "subject": "Roadmap sync"}]
    fake.tables["transcript_segments"] = [
        {"id": "segment-1", "sequence": 1, "speaker": "Asha", "text": "Ravi will send it."}
    ]
    fake.tables["meeting_participants"] = [
        {"display_name": "Ravi Sharma", "email": "ravi@example.com"},
        {"display_name": "Ravi Kumar", "email": "ravi.kumar@example.com"},
    ]
    fake.tables["profiles"] = [
        {"id": "user-1", "display_name": "Ravi Sharma", "email": "ravi@example.com"},
        {"id": "user-2", "display_name": "Ravi Kumar", "email": "ravi.kumar@example.com"},
    ]
    ai_result = ai_meetings.MeetingAIResult(
        summary="Follow-up needed.",
        key_points=[],
        decisions=[],
        tasks=[
            ai_meetings.MeetingAITask(
                title="Send follow-up",
                assignee_name="Ravi",
                evidence_segment_sequence=1,
            )
        ],
    )
    sent = []
    monkeypatch.setattr(ai_meetings, "supabase_gateway", fake)
    monkeypatch.setattr(ai_meetings, "_run_agno_meeting_agent", lambda *_: ai_result)
    monkeypatch.setattr(
        ai_meetings,
        "send_task_assignment_email",
        lambda **kwargs: sent.append(kwargs),
    )

    result = run(ai_meetings.generate_meeting_intelligence("meeting-1"))

    assert result["created_tasks_count"] == 1
    assert fake.tables["tasks"][0]["assignee_user_id"] is None
    assert fake.tables["tasks"][0]["notification_status"] == "not_sent"
    assert sent == []
```

- [ ] **Step 4: Implement participant/profile loading**

In `ai_meetings.py`, import:

```python
from app.services.assignee_resolution import resolve_assignee
from app.services.task_email import TaskEmailResult, send_task_assignment_email
```

Add:

```python
async def _get_meeting_participants(meeting_id: str) -> list[dict[str, Any]]:
    return await supabase_gateway.get(
        "meeting_participants",
        {"select": "*", "meeting_id": f"eq.{meeting_id}"},
    )


async def _get_profiles_for_participants(participants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    emails = sorted(
        {
            (participant.get("email") or participant.get("user_principal_name") or "").strip().lower()
            for participant in participants
            if participant.get("email") or participant.get("user_principal_name")
        }
    )
    if not emails:
        return []
    return await supabase_gateway.get(
        "profiles",
        {"select": "id,display_name,email", "email": f"in.({','.join(emails)})"},
    )
```

- [ ] **Step 5: Resolve assignees before storing action items**

Change `_store_action_items` signature to accept `participants` and `profiles`.

For each AI task:

```python
evidence_segment = _find_evidence_segment(transcript_segments, task.evidence_segment_sequence)
resolution = resolve_assignee(
    task.assignee_name,
    evidence_segment,
    participants,
    profiles,
)
```

Insert action item fields:

```python
"assignee_user_id": resolution.user_id,
"assignee_display_name": resolution.display_name or task.assignee_name,
"assignee_email": resolution.email,
"assignee_resolution_status": resolution.status,
"assignee_resolution_confidence": resolution.confidence,
"assignee_resolution_reason": resolution.reason,
```

Add:

```python
def _find_evidence_segment(
    transcript_segments: list[dict[str, Any]],
    sequence: int | None,
) -> dict[str, Any] | None:
    if sequence is None:
        return transcript_segments[-1] if transcript_segments else None
    return next(
        (segment for segment in transcript_segments if segment.get("sequence") == sequence),
        None,
    )
```

- [ ] **Step 6: Create tasks with resolved assignee**

In `_store_tasks_for_calendar_user`, use action item assignee fields:

```python
assignee_user_id = action_item.get("assignee_user_id")
assignee_email = action_item.get("assignee_email")
```

Task payload:

```python
"owner_user_id": meeting["user_id"],
"assignee_user_id": assignee_user_id,
"assignee_email": assignee_email,
"assignment_source": action_item.get("assignee_resolution_reason"),
"notification_status": "not_sent",
```

Only insert `task_assignees` rows for tasks with `assignee_user_id`.

- [ ] **Step 7: Send SMTP email after task insert**

After task insert:

```python
for task in tasks:
    if not task.get("assignee_email"):
        continue
    email_result = send_task_assignment_email(
        to_email=task.get("assignee_email"),
        assignee_name=task.get("assignee_email"),
        task=task,
        meeting=meeting,
    )
    update_payload = {
        "notification_status": "sent" if email_result.sent else email_result.reason,
        "notification_error": email_result.error,
    }
    if email_result.sent:
        update_payload["notification_sent_at"] = datetime.now(UTC).isoformat()
    await supabase_gateway.patch(
        "tasks",
        update_payload,
        params={"id": f"eq.{task['id']}", "limit": "1"},
    )
    task.update(update_payload)
```

- [ ] **Step 8: Run focused tests**

Run:

```powershell
python -m pytest backend\tests\test_ai_meetings_service.py backend\tests\test_assignee_resolution.py backend\tests\test_task_email.py -q
```

Expected: PASS.

---

## Task 10: Internal API Contract Tests

**Files:**
- Create: `backend/tests/test_bot_reporting_identity.py`

- [ ] **Step 1: Write ingestion contract test**

Create:

```python
import asyncio
from datetime import datetime, UTC


class FakeSupabaseGateway:
    def __init__(self):
        self.tables = {"transcript_segments": [], "meeting_participants": []}

    async def insert(self, path, payload):
        rows = payload if isinstance(payload, list) else [payload]
        self.tables[path].extend(rows)
        return rows

    async def upsert(self, path, payload, on_conflict=None):
        self.tables[path].append(payload)
        return [payload]


def run(coro):
    return asyncio.run(coro)


def test_record_bot_transcript_stores_speaker_identity(monkeypatch):
    from app.internal.schemas import BotTranscriptRequest, BotTranscriptSegment
    from app.services import bot_reporting

    fake = FakeSupabaseGateway()
    monkeypatch.setattr(bot_reporting, "supabase_gateway", fake)

    run(
        bot_reporting.record_bot_transcript(
            BotTranscriptRequest(
                meeting_id="meeting-1",
                segments=[
                    BotTranscriptSegment(
                        sequence=1,
                        speaker="Ravi Sharma",
                        source_id="7",
                        speaker_participant_id="participant-1",
                        speaker_aad_user_id="aad-ravi",
                        speaker_email="ravi@example.com",
                        speaker_user_principal_name="ravi@example.com",
                        text="I will send the notes.",
                        started_at=datetime.now(UTC),
                        ended_at=datetime.now(UTC),
                    )
                ],
            )
        )
    )

    assert fake.tables["transcript_segments"][0]["speaker_aad_user_id"] == "aad-ravi"
    assert fake.tables["meeting_participants"][0]["email"] == "ravi@example.com"
```

- [ ] **Step 2: Run contract test**

Run:

```powershell
python -m pytest backend\tests\test_bot_reporting_identity.py -q
```

Expected: PASS.

---

## Task 11: Configuration and Operational Checks

**Files:**
- Modify: `productivity-platform\backend\.env.example` if present
- Modify: `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot\appsettings.json`
- Modify: `productivity-platform\docs\contracts\bot-platform-api.md`

- [ ] **Step 1: Add backend SMTP env documentation**

Document these variables:

```env
TASK_EMAIL_ENABLED=true
TASK_SMTP_HOST=smtp.gmail.com
TASK_SMTP_PORT=587
TASK_SMTP_USERNAME=sender@example.com
TASK_SMTP_PASSWORD=app-password
TASK_SMTP_FROM_ADDRESS=sender@example.com
TASK_SMTP_FROM_NAME=MeetIQ
TASK_SMTP_ENABLE_TLS=true
```

- [ ] **Step 2: Confirm Graph permission**

In Azure app registration, confirm:

```text
Microsoft Graph application permission: User.Read.All
Admin consent: Granted
```

No `Mail.Send` permission is required because SMTP sends the assignment email.

- [ ] **Step 3: Update bot-platform contract**

In `docs/contracts/bot-platform-api.md`, update `POST /internal/bot/transcripts` segment example:

```json
{
  "sequence": 1,
  "speaker": "Ravi Sharma",
  "source_id": "7",
  "speaker_participant_id": "participant-1",
  "speaker_aad_user_id": "aad-ravi",
  "speaker_email": "ravi@example.com",
  "speaker_user_principal_name": "ravi@example.com",
  "language": "en-IN",
  "text": "I will send the notes.",
  "started_at": "2026-05-26T10:00:00Z",
  "ended_at": "2026-05-26T10:00:05Z"
}
```

---

## Task 12: End-to-End Verification

**Files:**
- No code changes.

- [ ] **Step 1: Run backend tests**

Run:

```powershell
python -m pytest backend\tests -q
```

Expected: PASS.

- [ ] **Step 2: Build .NET bot**

Run from `C:\Users\shweta.nagapure\TeamsMediaBot\TeamsMediaBot`:

```powershell
dotnet build
```

Expected: PASS.

- [ ] **Step 3: Run a controlled meeting transcript test**

Use an internal tenant meeting with two users:

```text
Speaker Ravi: I will send the pricing notes tomorrow.
Speaker Priya: I will update the customer tracker.
Speaker Asha: Ravi, please share the deck.
```

Expected:

- Ravi task assigned to Ravi profile/email.
- Priya task assigned to Priya profile/email.
- Deck task assigned to Ravi profile/email.
- SMTP sends one email per created task.
- No task is assigned to the calendar owner unless the calendar owner is the resolved assignee.

- [ ] **Step 4: Run ambiguity test manually**

Use a meeting with two internal users sharing the same first name and transcript line:

```text
Asha: Ravi will follow up.
```

Expected:

- Task is created with unresolved assignee.
- `notification_status` remains `not_sent`.
- No SMTP email is sent.

---

## Self-Review

- Spec coverage: participant identity capture, Graph user lookup using `User.Read.All`, backend identity ingestion, high-confidence assignment, SMTP sending, and unresolved safeguards are covered.
- Placeholder scan: no implementation step relies on `TODO`, `TBD`, or unspecified error handling.
- Type consistency: identity field names use snake_case in FastAPI/Supabase and camelCase in .NET JSON serialization, matching existing `JsonNamingPolicy.SnakeCaseLower` behavior in `PlatformBotReportingClient`.
- Scope check: external guests, anonymous users, phone users, and Graph `Mail.Send` are intentionally out of v1 scope.
