-- MeetIQ test user seed
-- Run after 001_initial_schema.sql.
-- This assumes the Supabase Auth user already exists.

insert into public.profiles (id, email, display_name, timezone)
values (
  '2329ecad-17ce-49f7-bf48-c7d3cc15d478',
  'person@company.com',
  'Test User',
  'Asia/Kolkata'
)
on conflict (id) do update set
  email = excluded.email,
  display_name = excluded.display_name,
  timezone = excluded.timezone,
  updated_at = now();

insert into public.calendar_connections (
  user_id,
  provider,
  tenant_id,
  aad_user_id,
  email,
  enabled,
  connection_status
)
values (
  '2329ecad-17ce-49f7-bf48-c7d3cc15d478',
  'microsoft',
  null,
  null,
  'person@company.com',
  true,
  'connected'
)
on conflict (user_id, provider) do update set
  tenant_id = excluded.tenant_id,
  aad_user_id = excluded.aad_user_id,
  email = excluded.email,
  enabled = excluded.enabled,
  connection_status = excluded.connection_status,
  updated_at = now();

insert into public.meeting_settings (
  user_id,
  auto_join_enabled,
  require_approval,
  approval_lead_minutes,
  look_ahead_minutes,
  join_early_seconds,
  max_late_join_minutes,
  leave_grace_minutes,
  use_service_hosted_media
)
values (
  '2329ecad-17ce-49f7-bf48-c7d3cc15d478',
  true,
  true,
  2,
  15,
  0,
  10,
  2,
  false
)
on conflict (user_id) do update set
  auto_join_enabled = excluded.auto_join_enabled,
  require_approval = excluded.require_approval,
  approval_lead_minutes = excluded.approval_lead_minutes,
  look_ahead_minutes = excluded.look_ahead_minutes,
  join_early_seconds = excluded.join_early_seconds,
  max_late_join_minutes = excluded.max_late_join_minutes,
  leave_grace_minutes = excluded.leave_grace_minutes,
  use_service_hosted_media = excluded.use_service_hosted_media,
  updated_at = now();

select * from public.bot_calendar_users;

