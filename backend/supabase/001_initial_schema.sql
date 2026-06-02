-- MeetIQ initial Supabase schema
-- Run this in the Supabase SQL editor for the platform project.

create extension if not exists pgcrypto;

create table if not exists public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    email text not null,
    display_name text,
    avatar_url text,
    role_title text,
    timezone text not null default 'UTC',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.organizations (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.organization_members (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references public.organizations(id) on delete cascade,
    user_id uuid not null references public.profiles(id) on delete cascade,
    role text not null default 'member',
    created_at timestamptz not null default now(),
    unique (organization_id, user_id)
);

create table if not exists public.calendar_connections (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.profiles(id) on delete cascade,
    provider text not null default 'microsoft',
    tenant_id text,
    aad_user_id text,
    email text not null,
    enabled boolean not null default true,
    connection_status text not null default 'pending',
    last_sync_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (user_id, provider)
);

create table if not exists public.meeting_settings (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.profiles(id) on delete cascade,
    auto_join_enabled boolean not null default false,
    require_approval boolean not null default true,
    approval_lead_minutes integer not null default 2,
    look_ahead_minutes integer not null default 15,
    join_early_seconds integer not null default 0,
    max_late_join_minutes integer not null default 10,
    leave_grace_minutes integer not null default 2,
    use_service_hosted_media boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (user_id)
);

create table if not exists public.meetings (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.profiles(id) on delete cascade,
    organization_id uuid references public.organizations(id) on delete set null,
    graph_event_id text not null,
    subject text not null,
    organizer_email text,
    join_url text,
    start_time timestamptz not null,
    end_time timestamptz not null,
    status text not null default 'detected',
    bot_status text not null default 'not_started',
    approval_status text not null default 'not_required',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (user_id, graph_event_id)
);

create table if not exists public.meeting_approvals (
    id uuid primary key default gen_random_uuid(),
    meeting_id uuid not null references public.meetings(id) on delete cascade,
    user_id uuid not null references public.profiles(id) on delete cascade,
    status text not null default 'pending',
    requested_at timestamptz not null default now(),
    expires_at timestamptz,
    decided_at timestamptz,
    decided_by text,
    decided_via text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.transcript_segments (
    id uuid primary key default gen_random_uuid(),
    meeting_id uuid not null references public.meetings(id) on delete cascade,
    sequence integer,
    speaker text,
    source_id text,
    speaker_participant_id text,
    speaker_aad_user_id text,
    speaker_email text,
    speaker_user_principal_name text,
    language text,
    text text not null,
    started_at timestamptz,
    ended_at timestamptz,
    created_at timestamptz not null default now()
);

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

create table if not exists public.meeting_summaries (
    id uuid primary key default gen_random_uuid(),
    meeting_id uuid not null references public.meetings(id) on delete cascade,
    summary text,
    key_points jsonb not null default '[]'::jsonb,
    decisions jsonb not null default '[]'::jsonb,
    model text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (meeting_id)
);

create table if not exists public.action_items (
    id uuid primary key default gen_random_uuid(),
    meeting_id uuid references public.meetings(id) on delete set null,
    assignee_user_id uuid references public.profiles(id) on delete set null,
    assignee_display_name text,
    assignee_email text,
    assignee_resolution_status text not null default 'unresolved',
    assignee_resolution_confidence numeric,
    assignee_resolution_reason text,
    title text not null,
    description text,
    status text not null default 'open',
    priority text not null default 'medium',
    due_date date,
    source_transcript_segment_id uuid references public.transcript_segments(id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.tasks (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid references public.organizations(id) on delete set null,
    owner_user_id uuid not null references public.profiles(id) on delete cascade,
    assignee_user_id uuid references public.profiles(id) on delete set null,
    assignee_email text,
    assignment_source text,
    notification_status text not null default 'not_sent',
    notification_sent_at timestamptz,
    notification_error text,
    meeting_id uuid references public.meetings(id) on delete set null,
    action_item_id uuid references public.action_items(id) on delete set null,
    title text not null,
    description text,
    status text not null default 'todo',
    priority text not null default 'medium',
    due_date date,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.task_assignees (
    id uuid primary key default gen_random_uuid(),
    task_id uuid not null references public.tasks(id) on delete cascade,
    user_id uuid not null references public.profiles(id) on delete cascade,
    role text not null default 'collaborator',
    created_at timestamptz not null default now(),
    unique (task_id, user_id)
);

create table if not exists public.ai_chat_messages (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.profiles(id) on delete cascade,
    role text not null,
    content text not null,
    sources jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.bot_events (
    id uuid primary key default gen_random_uuid(),
    bot_instance_id text not null,
    user_id uuid references public.profiles(id) on delete set null,
    meeting_id uuid references public.meetings(id) on delete set null,
    event_type text not null,
    severity text not null default 'info',
    message text not null,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.bot_heartbeats (
    id uuid primary key default gen_random_uuid(),
    bot_instance_id text not null unique,
    version text,
    status text not null default 'ok',
    last_seen_at timestamptz not null default now(),
    payload jsonb not null default '{}'::jsonb
);

create index if not exists idx_calendar_connections_enabled
    on public.calendar_connections(enabled, provider);

create index if not exists idx_meeting_settings_auto_join
    on public.meeting_settings(auto_join_enabled);

create index if not exists idx_meetings_user_start
    on public.meetings(user_id, start_time);

create index if not exists idx_transcript_segments_meeting_created
    on public.transcript_segments(meeting_id, created_at);

create index if not exists idx_meeting_participants_meeting
    on public.meeting_participants(meeting_id);

create index if not exists idx_meeting_participants_aad
    on public.meeting_participants(aad_user_id);

create index if not exists idx_transcript_segments_speaker_source
    on public.transcript_segments(meeting_id, source_id);

create index if not exists idx_transcript_segments_meeting_sequence
    on public.transcript_segments(meeting_id, sequence);

create index if not exists idx_tasks_owner_status
    on public.tasks(owner_user_id, status);

create index if not exists idx_task_assignees_user
    on public.task_assignees(user_id);

create index if not exists idx_task_assignees_task
    on public.task_assignees(task_id);

create index if not exists idx_bot_events_created
    on public.bot_events(created_at desc);

create or replace view public.bot_calendar_users as
select
    cc.user_id,
    cc.tenant_id,
    cc.aad_user_id,
    cc.email,
    ms.auto_join_enabled,
    ms.require_approval,
    ms.look_ahead_minutes,
    ms.approval_lead_minutes,
    ms.join_early_seconds,
    ms.max_late_join_minutes,
    ms.leave_grace_minutes
from public.calendar_connections cc
join public.meeting_settings ms on ms.user_id = cc.user_id
where
    cc.provider = 'microsoft'
    and cc.enabled = true
    and ms.auto_join_enabled = true;

alter table public.profiles enable row level security;
alter table public.organizations enable row level security;
alter table public.organization_members enable row level security;
alter table public.calendar_connections enable row level security;
alter table public.meeting_settings enable row level security;
alter table public.meetings enable row level security;
alter table public.meeting_approvals enable row level security;
alter table public.transcript_segments enable row level security;
alter table public.meeting_participants enable row level security;
alter table public.meeting_summaries enable row level security;
alter table public.action_items enable row level security;
alter table public.tasks enable row level security;
alter table public.task_assignees enable row level security;
alter table public.ai_chat_messages enable row level security;
alter table public.bot_events enable row level security;
alter table public.bot_heartbeats enable row level security;

create policy "Users can read own profile"
    on public.profiles for select
    using (auth.uid() = id);

create policy "Users can update own profile"
    on public.profiles for update
    using (auth.uid() = id);

create policy "Users can read own calendar connections"
    on public.calendar_connections for select
    using (auth.uid() = user_id);

create policy "Users can manage own meeting settings"
    on public.meeting_settings for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

create policy "Users can read own meetings"
    on public.meetings for select
    using (auth.uid() = user_id);

create policy "Users can read own tasks"
    on public.tasks for select
    using (auth.uid() = owner_user_id or auth.uid() = assignee_user_id);

create policy "Users can manage owned tasks"
    on public.tasks for all
    using (auth.uid() = owner_user_id)
    with check (auth.uid() = owner_user_id);

create policy "Users can read task assignees for their tasks"
    on public.task_assignees for select
    using (
        user_id = auth.uid()
        or exists (
            select 1
            from public.tasks t
            where t.id = task_id
              and (t.owner_user_id = auth.uid() or t.assignee_user_id = auth.uid())
        )
    );

create policy "Task owners can manage task assignees"
    on public.task_assignees for all
    using (
        exists (
            select 1
            from public.tasks t
            where t.id = task_id
              and t.owner_user_id = auth.uid()
        )
    )
    with check (
        exists (
            select 1
            from public.tasks t
            where t.id = task_id
              and t.owner_user_id = auth.uid()
        )
    );

create policy "Users can read own chat messages"
    on public.ai_chat_messages for select
    using (auth.uid() = user_id);
