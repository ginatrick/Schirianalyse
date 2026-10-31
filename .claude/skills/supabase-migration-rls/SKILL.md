---
name: supabase-migration-rls
description: Project rules for writing Supabase migrations with groups, roles and RLS in SchiriAnalyse. Use whenever a table, policy, trigger or database function is added or changed.
---
# Supabase migrations with RLS

## Files
- New file per change: `supabase/migrations/<timestamp>_<short_name>.sql`. Never edit an applied migration.
- Table and column names in English, snake_case.

## Every domain table
- `id uuid primary key default gen_random_uuid()`, `created_at timestamptz default now()`.
- `group_id uuid not null references groups(id)` plus an index on it.
- `alter table ... enable row level security;` in the same migration as the table.

## Roles
Roles live in `user_roles(user_id, group_id, role)` with role in `admin | observer | referee`. A person may hold several roles.
Use security-definer helper functions (create once, reuse in policies):
- `is_admin(group_id)`
- `is_observer_for_match(match_id)` via `observer_assignments` (by referee or by match, within valid_from/valid_to)
- `is_official_of_match(match_id)` via `match_officials` joined to `referees.user_id = auth.uid()`

## Policy pattern
- Admin: full access within the group.
- Observer: read matches/scenes of assigned referees or matches; insert/update own assessments; set `released`.
- Referee: read own matches (also as assistant); insert/update own self-assessment; read observer assessments only where `released = true`.
- AI rows in `assessments` (`source = 'ai'`) are written by the worker with the service role only.

## Notifications and jobs
- Notifications are created by triggers (analysis finished, assessment released, self-assessment completed, new comment), respecting `notification_settings`.
- `jobs` is the worker queue: status `queued | running | done | failed`, claimed with `for update skip locked`.

## Check before finishing
- Every new table: RLS on, policies for all three roles, index on `group_id` and foreign keys.
- Test policies with a referee, an observer and an admin test user (seed data), including the "not released yet" case.
