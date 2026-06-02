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

alter table public.meeting_participants enable row level security;
