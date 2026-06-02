-- Auth-backed onboarding policies.
-- Backend bootstrap currently uses the service-role key, but these policies keep
-- direct client-side onboarding possible without widening access to other users.

drop policy if exists "Users can insert own profile" on public.profiles;
drop policy if exists "Users can insert own calendar connections" on public.calendar_connections;
drop policy if exists "Users can update own calendar connections" on public.calendar_connections;

create policy "Users can insert own profile"
    on public.profiles for insert
    with check (auth.uid() = id);

create policy "Users can insert own calendar connections"
    on public.calendar_connections for insert
    with check (auth.uid() = user_id);

create policy "Users can update own calendar connections"
    on public.calendar_connections for update
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);
