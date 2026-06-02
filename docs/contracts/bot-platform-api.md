# Bot Platform API Contract

This contract defines how the deployed `.NET` Teams media bot collaborates with the MeetIQ FastAPI backend.

Base URL:

```text
https://<platform-api-host>
```

Local URL:

```text
http://localhost:8000
```

## Authentication

All internal bot endpoints require a service bearer token.

```http
Authorization: Bearer <BOT_INTERNAL_API_KEY>
```

The platform backend stores the expected key in:

```text
BOT_INTERNAL_API_KEY
```

## List Calendar Users

Used by the `.NET` bot to remove the hardcoded `CalendarAutoJoin:CalendarUserId` dependency.
The source of truth is the platform `bot_calendar_users` view, which is populated when
a Microsoft-authenticated user has a `profiles` row, an enabled Microsoft
`calendar_connections` row, and `meeting_settings.auto_join_enabled = true`.

```http
GET /internal/bot/calendar-users
```

Response:

```json
[
  {
    "user_id": "uuid",
    "tenant_id": "tenant-id",
    "aad_user_id": "graph-user-id",
    "email": "person@company.com",
    "auto_join_enabled": true,
    "require_approval": true,
    "look_ahead_minutes": 15,
    "approval_lead_minutes": 2,
    "join_early_seconds": 0,
    "max_late_join_minutes": 10,
    "leave_grace_minutes": 2
  }
]
```

Initial scaffold behavior:

```text
Returns an empty list until Supabase tables are added.
```

Dynamic onboarding behavior:

```text
POST /api/v1/onboarding/bootstrap
Authorization: Bearer <SUPABASE_ACCESS_TOKEN>
```

This creates or updates the logged-in user's profile, Microsoft calendar connection,
and meeting assistant settings. The user is not returned to the bot until the calendar
assistant is explicitly enabled.

## Bot Heartbeat

Used by the `.NET` bot to report that it is alive.

```http
POST /internal/bot/heartbeats
```

Request:

```json
{
  "bot_instance_id": "teams-bot-prod-1",
  "version": "1.0.0",
  "status": "ok",
  "payload": {}
}
```

Response:

```json
{
  "status": "accepted",
  "bot_instance_id": "teams-bot-prod-1",
  "received_at": "2026-05-15T10:30:00Z"
}
```

## Bot Event

Used by the `.NET` bot to report calendar, approval, join, audio, transcript, and error events.

```http
POST /internal/bot/events
```

Request:

```json
{
  "bot_instance_id": "teams-bot-prod-1",
  "user_id": "uuid",
  "meeting_id": "uuid",
  "event_type": "meeting_join_succeeded",
  "severity": "info",
  "message": "Bot joined the meeting successfully.",
  "payload": {}
}
```

Response:

```json
{
  "status": "accepted",
  "event_type": "meeting_join_succeeded",
  "received_at": "2026-05-15T10:30:00Z"
}
```

## Meeting, Transcript, and Approval Sync

```http
POST /internal/bot/meetings/upsert
POST /internal/bot/meetings/{meeting_id}/status
POST /internal/bot/transcripts
POST /internal/bot/approvals/upsert
POST /internal/bot/approvals/{approval_id}/decision
```

Transcript segments should include the bot-assigned sequence number so the platform
can display and analyze lines in the same order as the Blob archive.

```json
{
  "meeting_id": "platform-meeting-uuid",
  "segments": [
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
  ]
}
```

When the `.NET` bot creates an in-memory approval request, it should call:

```http
POST /internal/bot/approvals/upsert
```

Request:

```json
{
  "bot_approval_id": "bot-owned-approval-id",
  "meeting_id": "platform-meeting-uuid",
  "user_id": "platform-user-uuid",
  "status": "pending",
  "requested_via": "teams",
  "expires_at": "2026-05-19T09:10:00Z"
}
```

## Platform-To-Bot Approval Control

When a MeetIQ user approves or rejects from the platform UI, FastAPI calls the live `.NET` bot. The bot must be online according to `/internal/bot/heartbeats`; decisions are not queued while the bot is offline.

The bot should expose:

```http
POST /api/platform/approvals/{botApprovalId}/decision
Authorization: Bearer <BOT_INTERNAL_API_KEY>
```

Request:

```json
{
  "decision": "approve",
  "decided_by": "platform-user-uuid",
  "decided_via": "meetiq"
}
```

Response:

```json
{
  "status": "approved",
  "decided_by": "platform-user-uuid",
  "decided_via": "meetiq"
}
```

## Platform-To-Bot Manual Join

When a MeetIQ user clicks manual join in the platform UI, FastAPI calls the live `.NET` bot manual join endpoint. The `.NET` bot already exposes:

```http
POST /api/join
```

FastAPI calls:

```text
{TEAMS_BOT_BASE_URL}/api/join
```

If the user pastes a Teams URL or invite text that includes `meetingId` and `passcode`
values, FastAPI extracts those values and forwards them explicitly. Manually entered
`joinMeetingId` and `passcode` fields take precedence over extracted values.

Request:

```json
{
  "joinWebUrl": "https://teams.microsoft.com/l/meetup-join/...",
  "joinMeetingId": null,
  "passcode": null,
  "useServiceHostedMedia": false
}
```

Response:

```json
{
  "callId": "graph-call-id",
  "state": "establishing",
  "joinMode": "joinWebUrl",
  "mediaMode": "app-hosted",
  "message": "Call creation was accepted by Graph. Wait for callbacks to confirm the bot actually joined."
}
```
