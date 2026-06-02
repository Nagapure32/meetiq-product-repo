-- Preserve bot transcript ordering in Supabase.

alter table public.transcript_segments
    add column if not exists sequence integer;

create index if not exists idx_transcript_segments_meeting_sequence
    on public.transcript_segments(meeting_id, sequence);
