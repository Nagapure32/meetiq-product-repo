-- Shared meeting dedupe schema.
-- Allows multiple connected users to reference the same real Teams meeting
-- while keeping one durable bot-join identity.

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

create index if not exists idx_meeting_instances_start
    on public.meeting_instances(start_time);

create index if not exists idx_meeting_user_intents_user
    on public.meeting_user_intents(user_id, approval_status);

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
