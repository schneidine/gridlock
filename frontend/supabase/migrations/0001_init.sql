-- Sentinel Utilities schema: DESC x Georgia Power construction overlap detector.
--
-- Run this in the Supabase SQL Editor (or via `supabase db push`) against
-- a fresh Supabase project before running the seed script.

-- ---------------------------------------------------------------------
-- projects: both utilities' planned construction projects, one row each.
-- Keeps a `utility` discriminator instead of two separate tables, since
-- the schema is otherwise identical and the app always queries both
-- sides together.
-- ---------------------------------------------------------------------
create table if not exists projects (
  project_id        text primary key,       -- e.g. "DESC_1", "GPC_42"
  utility           text not null,          -- "Dominion Energy South Carolina" | "Georgia Power" | "Duke Energy"
  state             text not null,          -- "SC" | "GA" | "NC/SC"
  title             text not null,
  description       text,
  status            text,
  in_service_date   date,
  stations          text[] not null default '{}',
  geo_points         jsonb,                  -- [[lat,lon], ...] (1 or 2 endpoints)
  geo_center         jsonb,                  -- [lat, lon]
  geo_confidence      text,                   -- 'confirmed' | 'low_confidence'
  geo_notes           text[],
  created_at        timestamptz not null default now()
);

create index if not exists projects_utility_idx on projects (utility);

-- ---------------------------------------------------------------------
-- overlaps: every flagged DESC x GPC project pair under the 40km/25mi
-- threshold, precomputed by the Python pipeline and loaded by the seed
-- script. Re-running the pipeline + seed script replaces this table's
-- contents; it is not edited by hand or by the app.
-- ---------------------------------------------------------------------
create table if not exists "overlaps" (
  id                bigint generated always as identity primary key,
  project_id_a      text not null references projects (project_id) on delete cascade,
  project_id_b      text not null references projects (project_id) on delete cascade,
  distance_km       numeric not null,
  distance_mi       numeric not null,
  tier              text not null,           -- 'shared_substation' | 'same_window' | 'schedules_apart'
  day_gap           integer,
  confidence        text not null,
  created_at        timestamptz not null default now(),
  unique (project_id_a, project_id_b)
);

create index if not exists overlaps_tier_idx on "overlaps" (tier);
create index if not exists overlaps_distance_idx on "overlaps" (distance_km);

-- ---------------------------------------------------------------------
-- cost_impact: the bonus cost/impact estimate. Single row for now (one
-- flagged overlap gets the full estimate); structured so more rows can
-- be added later without a schema change.
-- ---------------------------------------------------------------------
create table if not exists cost_impact (
  id                          bigint generated always as identity primary key,
  overlap_id                  bigint references "overlaps" (id) on delete set null,
  desc_project_title          text not null,
  gpc_project_titles          text[] not null,
  distance_mi                 numeric not null,
  tier                        text not null,
  day_gap                     integer,
  location_note               text,
  desc_total_cost_usd         numeric,
  desc_cost_source            text,
  gpc_total_cost_usd          numeric,          -- null: CEII-redacted, never invented
  gpc_cost_note                text,
  savings_pct_low             numeric,
  savings_pct_high            numeric,
  savings_usd_low             numeric,
  savings_usd_high            numeric,
  benchmark_source             text,
  narrative                   text,
  created_at                  timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- planner_notes: the auth-gated collaboration feature. A logged-in user
-- (Supabase Auth) can leave a note on a flagged overlap. Publicly
-- readable (anyone viewing the app sees the notes), but only an
-- authenticated user can write one, and only their own account can
-- delete/edit it.
-- ---------------------------------------------------------------------
create table if not exists planner_notes (
  id            bigint generated always as identity primary key,
  overlap_id    bigint not null references "overlaps" (id) on delete cascade,
  user_id       uuid not null references auth.users (id) on delete cascade,
  author_label  text not null,      -- display name/email shown with the note
  body          text not null check (char_length(body) between 1 and 1000),
  created_at    timestamptz not null default now()
);

create index if not exists planner_notes_overlap_idx on planner_notes (overlap_id);

-- ---------------------------------------------------------------------
-- Row Level Security
-- ---------------------------------------------------------------------
alter table projects enable row level security;
alter table "overlaps" enable row level security;
alter table cost_impact enable row level security;
alter table planner_notes enable row level security;

-- Everyone (including anonymous visitors) can read the dataset -- it's a
-- public tool built on public filings, not user data.
create policy "public read projects" on projects for select using (true);
create policy "public read overlaps" on "overlaps" for select using (true);
create policy "public read cost_impact" on cost_impact for select using (true);
create policy "public read planner_notes" on planner_notes for select using (true);

-- Only the pipeline's service-role key can write to the dataset tables
-- (no policy granted for insert/update/delete to anon/authenticated --
-- service_role bypasses RLS entirely, which is what the seed script uses).

-- Only a signed-in user can add a note, and only as themselves.
create policy "authenticated users can insert their own notes" on planner_notes
  for insert
  to authenticated
  with check (auth.uid() = user_id);

-- Only the note's author can delete it.
create policy "users can delete their own notes" on planner_notes
  for delete
  to authenticated
  using (auth.uid() = user_id);
