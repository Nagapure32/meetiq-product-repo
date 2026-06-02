-- Uploaded recording ingestion path.
-- Keeps uploaded audio/video meetings isolated from Teams bot/live meeting ingestion.

alter table public.meetings
    add column if not exists source_type text not null default 'teams_live',
    add column if not exists processing_status text not null default 'not_started',
    add column if not exists uploaded_media_url text;

create table if not exists public.meeting_upload_jobs (
    id uuid primary key default gen_random_uuid(),
    meeting_id uuid not null references public.meetings(id) on delete cascade,
    user_id uuid not null references public.profiles(id) on delete cascade,
    status text not null default 'uploaded',
    original_filename text not null,
    content_type text,
    storage_path text,
    transcript_segment_count integer not null default 0,
    error_message text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_meetings_source_type
    on public.meetings(source_type);

create index if not exists idx_meeting_upload_jobs_user_status
    on public.meeting_upload_jobs(user_id, status);

alter table public.meeting_upload_jobs enable row level security;

create policy "Users can read own upload jobs"
    on public.meeting_upload_jobs for select
    using (auth.uid() = user_id);
