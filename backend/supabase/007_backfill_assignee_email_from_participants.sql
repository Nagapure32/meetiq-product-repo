with unique_participants as (
    select
        meeting_id,
        lower(regexp_replace(trim(display_name), '[[:space:]]+', ' ', 'g')) as normalized_display_name,
        min(email) as email,
        min(user_principal_name) as user_principal_name,
        count(*) as match_count
    from public.meeting_participants
    where display_name is not null
      and trim(display_name) <> ''
      and (email is not null or user_principal_name is not null)
    group by
        meeting_id,
        lower(regexp_replace(trim(display_name), '[[:space:]]+', ' ', 'g'))
    having count(*) = 1
),
updated_action_items as (
    update public.action_items action_item
    set
        assignee_email = coalesce(unique_participants.email, unique_participants.user_principal_name),
        assignee_resolution_status = 'resolved',
        assignee_resolution_confidence = coalesce(
            action_item.assignee_resolution_confidence,
            0.9
        ),
        assignee_resolution_reason = coalesce(
            action_item.assignee_resolution_reason,
            'unique_participant_display_name_backfill'
        ),
        updated_at = now()
    from unique_participants
    where action_item.meeting_id = unique_participants.meeting_id
      and action_item.assignee_email is null
      and action_item.assignee_display_name is not null
      and lower(regexp_replace(trim(action_item.assignee_display_name), '[[:space:]]+', ' ', 'g'))
        = unique_participants.normalized_display_name
    returning action_item.id, action_item.assignee_email
)
update public.tasks task
set
    assignee_email = updated_action_items.assignee_email,
    assignment_source = coalesce(
        task.assignment_source,
        'unique_participant_display_name_backfill'
    ),
    updated_at = now()
from updated_action_items
where task.action_item_id = updated_action_items.id
  and task.assignee_email is null;
