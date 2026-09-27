-- Cache of Gemini "AI insights" summaries, one per flagged pair, so each
-- pair only costs a Gemini call the first time (or when someone hits
-- Regenerate). Rows cascade away when seed.mjs replaces the overlaps.
create table if not exists overlap_insights (
  overlap_id  bigint primary key references "overlaps" (id) on delete cascade,
  body        text not null,
  model       text not null,
  created_at  timestamptz not null default now()
);

alter table overlap_insights enable row level security;

create policy "public read overlap_insights" on overlap_insights for select using (true);

-- No insert/update policy: only the server (service-role key, which
-- bypasses RLS) writes here, from src/app/actions/insights.ts.
