-- Multi-assignee support for tasks.

create table if not exists public.task_assignees (
    id uuid primary key default gen_random_uuid(),
    task_id uuid not null references public.tasks(id) on delete cascade,
    user_id uuid not null references public.profiles(id) on delete cascade,
    role text not null default 'collaborator',
    created_at timestamptz not null default now(),
    unique (task_id, user_id)
);

create index if not exists idx_task_assignees_user
    on public.task_assignees(user_id);

create index if not exists idx_task_assignees_task
    on public.task_assignees(task_id);

alter table public.task_assignees enable row level security;

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
