# Gridlock — Web App

Next.js 16 + Supabase (Postgres + Auth) + Vercel deployment of the Gridlock
dashboard: an interactive map and ranked list of geographic/timeline overlaps
between Dominion Energy South Carolina (DESC) and Georgia Power (GPC) planned
transmission construction projects, built for the ShellHacks 2026 Sperry
Tech "Gridlock" challenge (FERC Order No. 1920 motivation).

This app reads from Supabase Postgres tables (`projects`, `overlaps`,
`cost_impact`, `planner_notes`), which are seeded from the reproducible data
pipeline in `../backend/pipeline/` (see the repo root `README.md` for how that JSON
is generated from the raw utility filings).

Viewing the map, ranked list, and bonus cost/impact panel needs no account.
Signing in (Supabase magic-link email auth) unlocks leaving planner notes on
a flagged overlap — a lightweight "coordination workspace" layer on top of
the data.

## 1. Create a Supabase project

1. Go to [supabase.com](https://supabase.com/dashboard) and create a new
   project (any region is fine).
2. Once it's provisioned, go to **Project Settings → API** and note:
   - **Project URL** → `NEXT_PUBLIC_SUPABASE_URL`
   - **anon public key** → `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - **service_role key** → `SUPABASE_SERVICE_ROLE_KEY` (⚠️ never expose this
     to the browser or commit it — it bypasses Row Level Security)

## 2. Run the database migration

In the Supabase dashboard, open **SQL Editor**, paste the contents of
[`supabase/migrations/0001_init.sql`](./supabase/migrations/0001_init.sql),
and run it. This creates the four tables (`projects`, `overlaps`,
`cost_impact`, `planner_notes`), enables Row Level Security on all of them,
and adds the policies:

- `projects`, `overlaps`, `cost_impact`: public `select` (anyone can view the
  map/list/cost panel with no account).
- `planner_notes`: public `select`, but `insert`/`delete` require
  `auth.uid()` to match the note's `user_id` (only signed-in users can post
  or remove their own notes).

(If you'd rather use the Supabase CLI: `supabase link` then
`supabase db push` with this file in `supabase/migrations/`.)

## 3. Configure the magic-link auth email template

Supabase's default confirmation email uses an older `#access_token=`
redirect style. This app uses the SSR-recommended `token_hash` flow via a
route handler at `/auth/confirm`, so the email template needs to point
there:

1. In the Supabase dashboard, go to **Authentication → Email Templates →
   Magic Link**.
2. Replace the confirmation URL in the template body with:

   ```
   {{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=email&next=/
   ```

3. Save. (Do this for both your local/dev project and, if you create a
   separate one, your production project.)

## 4. Set environment variables

Copy `.env.example` to `.env.local` and fill in the three values from step 1:

```bash
cp .env.example .env.local
```

```
NEXT_PUBLIC_SUPABASE_URL=https://xxxxxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

`.env.local` is gitignored — never commit it. When you deploy to Vercel,
add the same three variables under **Project Settings → Environment
Variables** (all three as "Production" + "Preview" + "Development"; the
service-role key is only read server-side by the seed script and never by
the deployed app itself, but Vercel needs it if you ever run the seed script
via a Vercel-hosted job).

## 5. Install dependencies and seed the database

```bash
npm install
node scripts/seed.mjs
```

The seed script reads the pipeline's output JSON from
`../backend/data_clean/{gridlock_dataset.json,cost_impact_estimate.json}` and
upserts it into your Supabase tables using the service-role key (bypasses
RLS, so it must only ever be run from a trusted machine — never in the
browser). Re-run it any time the underlying data pipeline output changes.

## 6. Run locally

```bash
npm run dev
```

Visit `http://localhost:3000`. The map and ranked list should populate
immediately from Supabase; use "Sign in" in the header to test the
magic-link flow (check the email inbox you used, click the link, and you
should land back on `/` signed in and able to post a note on an overlap).

## 7. Deploy to Vercel

```bash
npx vercel
```

or connect the GitHub repo at [vercel.com/new](https://vercel.com/new) and
let it auto-detect Next.js. Either way, set the same three environment
variables in the Vercel project settings before the first deploy (or
redeploy after adding them). No other build configuration is required —
Vercel's default Next.js build/output settings work as-is.

## Project structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx            # server component root: fetches data + auth state
│   │   ├── login/page.tsx      # magic-link sign-in form
│   │   ├── auth/confirm/route.ts  # exchanges token_hash for a session
│   │   └── actions/auth.ts     # sign-out server action
│   ├── components/
│   │   ├── Dashboard.tsx       # client orchestrator (map + list + panel)
│   │   ├── GridlockMap.tsx     # react-leaflet map (dynamically imported, ssr:false)
│   │   ├── OverlapList.tsx     # ranked, tier-filterable overlap list
│   │   ├── NoteThread.tsx      # planner notes (insert requires auth)
│   │   ├── CostImpactPanel.tsx # bonus cost/impact estimate panel
│   │   └── HeaderAuth.tsx      # sign-in link / sign-out form
│   ├── lib/
│   │   ├── supabase/{client,server}.ts  # browser + server Supabase clients
│   │   ├── data.ts             # server-side data fetchers
│   │   └── types.ts            # shared TS types
│   └── proxy.ts                # Supabase session-refresh (Next 16's renamed middleware)
├── supabase/migrations/0001_init.sql  # schema + RLS policies
├── scripts/seed.mjs            # loads ../backend/data_clean/*.json into Supabase
└── .env.example
```

## Notes

- This app was scaffolded on **Next.js 16.3.6**, which renamed
  `middleware.ts` → `proxy.ts` (same behavior, new file/function name — see
  `src/proxy.ts`). If you upgrade Next.js further, check
  `node_modules/next/dist/docs/` for any newer breaking changes before
  editing routing/auth code.
- Fonts are a plain system-font stack (not `next/font/google`) because the
  build environment used to develop this app couldn't reach
  `fonts.googleapis.com`; swap in a real webfont if you want one and your
  deploy target can reach Google Fonts.
- GPC's project costs are redacted in their public filing as Critical Energy
  Infrastructure Information (CEII). `cost_impact` intentionally has no
  invented number for GPC — see `../backend/pipeline/cost_impact.py` and the
  `CostImpactPanel` methodology note for what is and isn't estimated, and why.
