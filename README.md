# Gridlock — DESC × Georgia Power Coordination Tool

ShellHacks 2026 — Sperry Tech Gridlock Challenge

## What this is

Compares Dominion Energy South Carolina's and Georgia Power's real, public
future-construction plans and flags where their planned transmission work
overlaps geographically and/or in time, so the two utilities could
potentially share crews, equipment, or right-of-way.

## Structure

```
backend/
  data_raw/
    utility-filings/    the two real source documents (DESC PDF, GPC IRP text)
    challenge-brief/    organizer materials (challenge doc, worked example, geocoding guide)
  data_clean/           parsed project lists + generated JSON the app reads
  pipeline/             the full pipeline, runnable end-to-end from data_raw/ (see below)
  requirements.txt
frontend/              Next.js + Supabase dashboard (the real deliverable; see frontend/README.md)
web/                    static Leaflet demo, reads the JSON directly (open web/index.html via a local server)
```

## Running it

```bash
cd backend
pip install -r requirements.txt

mac:
python3 -m pip install -r requirements.txt

cd pipeline
python3 parse_desc_pdf.py     # data_raw/utility-filings/*.pdf -> ../data_clean/desc_projects_raw.json
python3 parse_gpc_irp.py      # data_raw/utility-filings/*.txt -> ../data_clean/gpc_projects_raw.json
python3 build_dataset.py      # -> ../data_clean/gridlock_dataset.json (the overlap engine)
python3 cost_impact.py        # -> ../data_clean/cost_impact_estimate.json (bonus estimate)

cp ../data_clean/gridlock_dataset.json ../data_clean/cost_impact_estimate.json ../../web/data/
cd ../../web && python3 -m http.server 8000    # then open http://localhost:8000
```

For the full Next.js + Supabase dashboard instead of the static demo, see
`frontend/README.md`.

The whole chain is reproducible from the two raw filings in `backend/data_raw/utility-filings/`
straight through to the final dataset — nothing is hand-patched or only exists
as a cached JSON file.

## Data sources

- **DESC**: "Planned Transmission Projects $2M and Above" 5-Year Budget PDF — 44 real
  projects, fully public (name, description, need, status, in-service date).
- **Georgia Power**: 2025 IRP Technical Appendix Volume 3, Table 2 ("Georgia ITS
  10-Year Expansion Plan Projects List") — 208 rows across all ITS participants;
  filtered to the 138 rows sponsored by Georgia Power itself (including its
  Savannah-division "SAV:" projects). **Cost figures in this filing are CEII-redacted
  and are not used** — only public fields (name, zone, need date) feed the pipeline.

## Methodology

1. **Parse** both filings into structured project rows (`parse_desc_pdf.py`,
   `parse_gpc_irp.py`).
2. **Extract station names** from each project title using the voltage marker
   (e.g. "115 kV") as the split point between the two named substations —
   validated exactly against the organizers' own worked example
   (`Projects_Overlaps.xlsx`).
3. **Geocode** each station via `backend/pipeline/coords_seed.py`, a hand-built
   gazetteer with three honesty tiers:
   - `confirmed` — taken directly from the organizers' validated example, or
     is a real named town/city with well-known coordinates.
   - `estimated` — interpolated from known points on the same line, used
     where no direct place match exists.
   - `region_only` — a broad service-area stand-in (e.g. "Charleston, SC" or
     "Atlanta, GA"), used only to prove a project is nowhere near the border
     and therefore correctly excluded — not precise enough to trust for a
     close-tier call.
   *(Public, per-substation coordinate data is genuinely sparse — this
   mirrors a real constraint the challenge brief itself calls out. Overpass/
   Nominatim were not reachable from this environment, so higher-confidence
   town/place matches and interpolation were used instead of blind API geocoding.)*
4. **Distance**: haversine closest-point distance between every DESC × GPC
   project pair (using both named endpoints where known, not just centroids).
5. **Flag & rank** any pair under 40 km / 25 mi into four tiers (touching/
   crossing, <1.6 km, <8 km, <40 km), and record the day-gap between planned
   in-service dates as a secondary signal.
6. **Validated** against the organizers' 6 known ground-truth overlaps — the
   pipeline reproduces all of them, plus surfaces new real overlaps found by
   using the full 44+138 project dataset instead of the 10-project example.

## Bonus: cost/impact estimate

`backend/pipeline/cost_impact.py` builds a rough savings estimate for the strongest
flagged overlap (DESC's "Hooks - Thurmond 115kV Tie: Rebuild" vs. Georgia
Power's two "Evans Primary - Thurmond Dam" rebuilds — the same facility on
the Savannah River, 0.0 mi apart per the organizers' own confirmed
coordinates, currently scheduled 8.4 years apart). Every number is either
pulled directly from a real public filing or an industry-documented figure
applied as a range, never invented:

The saving is framed as "one mobilization instead of two":

- DESC's cost ($23,787,423, 6.5 mi of line, ~$3.7M/mi) comes straight from
  its public budget filing.
- Georgia Power's cost is CEII-redacted in the IRP; the tool says so and never
  estimates it. DESC's cost is used only as a proxy for job scale.
- Mobilization (crew travel, equipment haul, staging yard, site setup, access,
  safety stand-up) is assumed to be 3–5% of contract cost, a conservative
  range under the ~10% cap many state DOT specs put on that pay item. That
  gives **~$0.7M–$1.2M**, before any shared right-of-way or outage-window
  savings.
- The NYC DDC 2025 Utility Coordination Report (coordinated projects saw ~74%
  lower utility-delay cost) is cited only as context that this is a floor. It
  covers urban underground work, so it isn't applied directly.

This appears as a highlighted panel at the top of the app's sidebar, with an
expandable methodology note.

## Known limitations / next steps

- Not every substation is in OpenStreetMap: 7 DESC and 36 GPC projects have
  no located endpoint and can't be placed, and 16 DESC / 42 GPC projects rest
  on `low_confidence` matches. The UI and xlsx flag these rather than hiding them.
- The SERTP 2025 regional and preliminary plans are downloaded and registered
  in `pipeline/sources.py` but not parsed yet.
- No backend API yet — the UI reads the static generated JSON directly;
  fine for a hackathon demo, easy to swap for a FastAPI endpoint later.
- Leaflet is vendored locally under `web/vendor/leaflet/` (not loaded from a
  CDN) so the app has zero external JS dependencies and can't break on
  flaky venue wifi. The basemap tiles themselves still load from a public
  tile server (OpenStreetMap) at runtime, which needs normal internet access — this
  was verified working end-to-end with a headless-browser screenshot test,
  not just "should work."
