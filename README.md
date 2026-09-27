# Gridlock — DESC × Georgia Power Coordination Tool

ShellHacks 2026 — Sperry Tech Gridlock Challenge

## What this is

Compares Dominion Energy South Carolina's and Georgia Power's real, public
future-construction plans and flags where their planned transmission work
overlaps geographically and/or in time, so the two utilities could
potentially share crews, equipment, or right-of-way.

## Structure

```
data_raw/
  utility-filings/    the two real source documents (DESC PDF, GPC IRP text)
    sertp/            SERTP 2025 regional + preliminary expansion plans (not parsed yet)
  challenge-brief/    organizer materials (challenge doc, worked example, geocoding guide)
data_clean/           parsed project lists + generated JSON the app reads
pipeline/             the full pipeline, runnable end-to-end from data_raw/ (see below)
  sources.py          registry of every source document: input path, output path, parser
web/                  the interactive map + ranked-list UI (open web/index.html via a local server)
```

## Running it

```bash
pip install -r requirements.txt

mac:
python3 -m pip install -r requirements.txt

cd pipeline
python3 parse_desc_pdf.py     # data_raw/utility-filings/*.pdf -> data_clean/desc_projects_raw.json
python3 parse_gpc_irp.py      # data_raw/utility-filings/*.txt -> data_clean/gpc_projects_raw.json
python3 build_dataset.py      # geocode + overlap engine -> data_clean/gridlock_dataset.json,
                              #   Projects_Overlaps.xlsx, projects.csv, overlaps.csv, *.geojson
python3 cost_impact.py        # -> data_clean/cost_impact_estimate.json (bonus estimate)

cp ../data_clean/gridlock_dataset.json ../data_clean/cost_impact_estimate.json ../web/data/
cd ../web && python3 -m http.server 8000    # then open http://localhost:8000
```

The whole chain is reproducible from the two raw filings in `data_raw/utility-filings/`
straight through to the final dataset — nothing is hand-patched. The only cached
inputs are the OpenStreetMap pulls in `data_raw/osm/` (Overpass substations +
Nominatim lookups), kept so reruns don't depend on those public APIs being up.

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
   (e.g. "115 kV") as the split point between the two named substations.
3. **Geocode** each station with `pipeline/geocode.py`, in priority order:
   - the organizers' worked example (`Projects_Overlaps_organizer_example.xlsx`)
     when it already pins the station — treated as ground truth, with our own
     OSM match recorded as a cross-check;
   - OpenStreetMap `power=substation` features across GA + SC (one Overpass
     pull), fuzzy-matched with rapidfuzz and filtered to the right utility's
     operator tags;
   - Nominatim for the town the station is named after, always `low_confidence`.

   Every match is then validated (name score, operator, same-name ambiguity,
   GPC planning-zone proximity, DESC state box, plausible line span). A match
   that fails the zone/state check is **rejected** and the endpoint left
   unlocated rather than guessed. Each endpoint ends up `confirmed`,
   `low_confidence`, `unlocated` or `rejected`, and the reasons are written
   into the dataset and the xlsx `endpoint_validation` sheet.
4. **Distance**: a project's center is the midpoint of its located endpoints;
   haversine distance is computed for every DESC × GPC center pair.
5. **Flag & rank**: every pair under 25 miles is an overlap, with the day gap
   between in-service dates. Ranked by
   `score = 0.7 · (1 − dist/25) + 0.3 · (1 − min(gap, 1825)/1825)`
   (timing gaps beyond 5 years add nothing).
6. **Validated** against the organizers' 6 known overlaps: all 6 reproduced
   (distances match to within 0.2 mi, day gaps exactly). The full
   44 + 138 project run surfaces 44 overlaps in total.

## Bonus: cost/impact estimate

`pipeline/cost_impact.py` reads the ranked overlap table and prices the
top-ranked confirmed pair whose DESC side has a public cost. Currently that is
DESC's **Jasper – Okatie 230 kV #2: Construct** vs. Georgia Power's
**SAV: McIntosh – Purrysburg 230 kV Reactors**: 5.65 mi apart, due 152 days
apart, on the same 230 kV corridor across the Savannah River.

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
  tile server (CARTO) at runtime, which needs normal internet access — this
  was verified working end-to-end with a headless-browser screenshot test,
  not just "should work."
