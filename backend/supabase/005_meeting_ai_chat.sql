-- Meeting-scoped AI chat and Azure AI Search indexing status.

alter table public.ai_chat_messages
    add column if not exists meeting_id uuid references public.meetings(id) on delete cascade;

create table if not exists public.meeting_ai_indexes (
    id uuid primary key default gen_random_uuid(),
    meeting_id uuid not null references public.meetings(id) on delete cascade,
    user_id uuid not null references public.profiles(id) on delete cascade,
    status text not null default 'not_indexed',
    indexed_chunk_count integer not null default 0,
    transcript_segment_count integer not null default 0,
    indexed_at timestamptz,
    error_message text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (meeting_id)
);

create index if not exists idx_ai_chat_messages_meeting_created
    on public.ai_chat_messages(meeting_id, created_at);

create index if not exists idx_meeting_ai_indexes_user_status
    on public.meeting_ai_indexes(user_id, status);

alter table public.meeting_ai_indexes enable row level security;

drop policy if exists "Users can read own chat messages" on public.ai_chat_messages;

create policy "Users can read own meeting chat messages"
    on public.ai_chat_messages for select
    using (auth.uid() = user_id);

create policy "Users can read own meeting AI indexes"
    on public.meeting_ai_indexes for select
    using (auth.uid() = user_id);
