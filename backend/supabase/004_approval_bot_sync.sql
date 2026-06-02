-- Link platform approval rows to the .NET bot's in-memory approval IDs.

alter table public.meeting_approvals
add column if not exists bot_approval_id text;

alter table public.meeting_approvals
add column if not exists requested_via text;

create unique index if not exists idx_meeting_approvals_bot_approval_id
on public.meeting_approvals(bot_approval_id)
where bot_approval_id is not null;

create index if not exists idx_meeting_approvals_user_requested
on public.meeting_approvals(user_id, requested_at desc);
