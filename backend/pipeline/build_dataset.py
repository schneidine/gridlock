"""
Sentinel Utilities overlap-detection pipeline.

Loads the parsed DESC, GPC and Duke Energy project lists (Duke from the SERTP
Non-CEII preliminary plan), geocodes every named endpoint
against OpenStreetMap (pipeline/geocode.py, with validation + confidence
flags), and builds the overlap table exactly as the challenge defines it:

  - center point = midpoint of the project's two named sub-points, i.e. the route
    ends (one located point -> that point), per Finding_Real_Locations_Guide.docx
  - haversine distance between every pair of projects from two different utilities
    (DESC x GPC, DESC x Duke, GPC x Duke)
  - every pair under 25 miles is one overlap row, with the in-service day gap
  - ranked by score = 0.7 * (1 - dist/25) + 0.3 * (1 - min(gap, 1825)/1825)

Each overlap also gets an "opportunity" category saying what the two projects
could realistically share. The challenge only defines the 25 mi / day-gap
overlap; these rules are ours, based on evidence rather than distance bands:

  - shared_substation: both projects work at the same substation (located
    endpoints within 0.5 km), so the work there has to be coordinated
  - same_window:       in-service dates within 2 years, so crews, equipment,
                       staging yards and deliveries could be shared
  - schedules_apart:   within 25 mi but built more than 2 years apart (or a date
                       is unknown), so there is little to share beyond planning
It is stored in the "tier" field, the column the Supabase schema already has.

Outputs (data_clean/):
  sentinel_dataset.json        what the web UI reads
  Projects_Overlaps.xlsx       projects / overlaps sheets in the organizer's format,
                               plus endpoint_validation and data_quality sheets
  projects.csv, overlaps.csv
  desc_projects.geojson, gpc_projects.geojson, duke_projects.geojson
"""
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from geocode import Geocoder, geocode_project, haversine_km, route_ends

ROOT = Path(__file__).parent.parent
CLEAN = ROOT / "data_clean"
SERTP_RAW = CLEAN / "sertp_2025_preliminary_plan_projects_raw.json"
ORGANIZER_XLSX = ROOT / "data_raw" / "challenge-brief" / "Projects_Overlaps_organizer_example.xlsx"

KM_PER_MI = 1.609344
THRESHOLD_MI = 25.0
MAX_GAP_DAYS = 1825  # 5 years: beyond this, timing no longer helps coordination
W_DIST, W_TIME = 0.7, 0.3
KEEP_SPONSORS = ("GPC", "SAV")  # SAV = Georgia Power's Savannah division
CONF_RANK = {"confirmed": 0, "low_confidence": 1}
SHARED_STATION_KM = 0.5    # endpoints this close are the same substation
BUILD_WINDOW_DAYS = 730    # our assumption: builds within 2 years can share crews and equipment


def parse_date(s):
    """Handles '12/31/23', '6/1/2026' and '10/1/2025 (phase 1) and ...' (first date wins)."""
    if not s:
        return None
    m = re.search(r"\d{1,2}/\d{1,2}/\d{2,4}", str(s))
    if not m:
        return None
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(m.group(), fmt)
        except ValueError:
            continue
    return None


def shared_stations(pa, pb):
    """Names of substations both projects touch, matched by location (names differ across utilities).
    An endpoint placed by an unresolved same-name guess is not evidence of a shared station."""
    def solid(e):
        return e["pt"] and (e["checks"] or {}).get("ambiguous_resolved", True)
    return [
        f"{ea['name']} / {eb['name']}"
        for ea in pa["endpoints"] if solid(ea)
        for eb in pb["endpoints"] if solid(eb) and haversine_km(ea["pt"], eb["pt"]) <= SHARED_STATION_KM
    ]


def opportunity(shared, gap_days):
    """What the pair could realistically share (see module docstring)."""
    if shared:
        return "shared_substation"
    if gap_days is not None and gap_days <= BUILD_WINDOW_DAYS:
        return "same_window"
    return "schedules_apart"


def score(dist_mi, gap_days):
    gap = MAX_GAP_DAYS if gap_days is None else min(gap_days, MAX_GAP_DAYS)
    return round(W_DIST * (1 - dist_mi / THRESHOLD_MI) + W_TIME * (1 - gap / MAX_GAP_DAYS), 4)


def service_window(raw):
    """(earliest, latest) in-service date the source allows: one day for a full date,
    Jan 1 - Dec 31 when the source gives only a year (SERTP lists Duke projects that way)."""
    if re.fullmatch(r"\s*\d{4}\s*", str(raw or "")):
        year = int(raw)
        return datetime(year, 1, 1), datetime(year, 12, 31)
    d = parse_date(raw)
    return (d, d) if d else None


def day_gap(raw_a, raw_b):
    """Days between two in-service dates; for a year-only date, the smallest gap that year allows."""
    wa, wb = service_window(raw_a), service_window(raw_b)
    if not wa or not wb:
        return None
    if wa[1] < wb[0]:
        return (wb[0] - wa[1]).days
    if wb[1] < wa[0]:
        return (wa[0] - wb[1]).days
    return 0


def date_note(raw, parsed):
    if parsed is None:
        return f"unparseable in-service date '{raw}'"
    if not re.fullmatch(r"\s*\d{1,2}/\d{1,2}/\d{2,4}\s*", str(raw)):
        return f"in-service date '{raw}' has extra text; used first date {parsed:%Y-%m-%d}"
    return None


def make_project(pid, utility, state, title, raw_date, stations, geo, **extra):
    year_only = bool(re.fullmatch(r"\s*\d{4}\s*", str(raw_date or "")))
    d = None if year_only else parse_date(raw_date)
    notes = list(extra.pop("data_quality_flags", []))
    if year_only:
        notes.append("source gives only the in-service year; day gaps to this project are the "
                     "smallest gap that year allows")
    elif date_note(raw_date, d):
        notes.append(date_note(raw_date, d))
    located = [e for e in geo["endpoints"] if e["pt"]]
    return {
        "project_id": pid,
        "utility": utility,
        "state": state,
        "title": title,
        "in_service_date_raw": raw_date,
        "in_service_date": d.date().isoformat() if d else None,
        "in_service_year": int(raw_date) if year_only else (d.year if d else None),
        "stations": stations,
        **extra,
        "data_quality_flags": notes,
        "geo": None if geo["center"] is None else {
            "points": [e["pt"] for e in located],
            "center": geo["center"],
            "confidence": geo["confidence"],
            "notes": geo["notes"],
            "geocode_notes": geo["notes"],  # name the frontend seed script reads
        },
        "endpoints": [
            {k: e.get(k) for k in ("name", "pt", "source", "confidence", "checks", "notes", "rejected_source")}
            for e in geo["endpoints"]
        ],
    }


def build_projects():
    desc_raw = json.load(open(CLEAN / "desc_projects_raw.json"))
    gpc_all = json.load(open(CLEAN / "gpc_projects_raw.json"))
    gpc_raw = [p for p in gpc_all if p.get("sponsor") in KEEP_SPONSORS]
    duke_raw = [p for p in json.load(open(SERTP_RAW)) if (p["balancing_authority"] or "").startswith("DUKE")]

    geocoder = Geocoder()
    anchors = geocoder.build_zone_centroids(gpc_raw)
    print(f"OSM: {len(geocoder.osm)} named substations in GA/SC/NC")
    print(f"GPC zone centroids from unambiguous OSM anchors: "
          f"{ {z: anchors[z] for z in sorted(geocoder.zone_centroids)} }")

    desc = []
    for i, p in enumerate(desc_raw, 1):
        geo = geocode_project(p["stations"], "DESC", geocoder)
        desc.append(make_project(
            f"DESC_{i}", "Dominion Energy South Carolina", "SC", p["title"], p["in_service_date"],
            p["stations"], geo,
            source_project_id=p["project_id_raw"], description=p["description"], status=p["status"],
            total_cost_usd=p["total_cost_usd"], yearly_cost_usd=p.get("yearly_cost_usd"),
            data_quality_flags=p.get("data_quality_flags", []),
        ))
    gpc = []
    for i, p in enumerate(gpc_raw, 1):
        geo = geocode_project(p["stations"], "GPC", geocoder, zone=p["zone"])
        gpc.append(make_project(
            f"GPC_{i}", "Georgia Power", "GA", re.sub(r"[\x00-\x1f]", "", p["project_name"]),
            p["need_date"], p["stations"], geo,
            teams_number=p["teams_number"], zone=p["zone"], sponsor=p["sponsor"],
        ))
    duke = []
    for i, p in enumerate(duke_raw, 1):
        geo = geocode_project(p["stations"], "DUKE", geocoder)
        duke.append(make_project(
            f"DUKE_{i}", "Duke Energy", "NC/SC", p["project_name"], str(p["in_service_year"]),
            p["stations"], geo,
            description=p["description"], balancing_authority=p["balancing_authority"],
            source_page=p["page"],
            data_quality_flags=p["data_quality_flags"],
        ))
    geocoder.nom.save()
    return desc, gpc, duke, len(gpc_all) - len(gpc_raw)


def overlap_row(pa, pb):
    """The overlap-table row for two projects, or None if either is unlocated or they are >= 25 mi apart."""
    if not pa["geo"] or not pb["geo"]:
        return None
    dist_mi = haversine_km(pa["geo"]["center"], pb["geo"]["center"]) / KM_PER_MI
    if dist_mi >= THRESHOLD_MI:
        return None
    gap = day_gap(pa["in_service_date_raw"], pb["in_service_date_raw"])
    shared = shared_stations(pa, pb)
    return {
        "project_id_a": pa["project_id"], "project_a_title": pa["title"], "utility_a": pa["utility"],
        "project_id_b": pb["project_id"], "project_b_title": pb["title"], "utility_b": pb["utility"],
        "distance_mi": round(dist_mi, 2),
        "distance_km": round(dist_mi * KM_PER_MI, 2),
        "tier": opportunity(shared, gap),
        "shared_stations": shared,
        "day_gap": gap,
        "score": score(dist_mi, gap),
        "confidence": max(pa["geo"]["confidence"], pb["geo"]["confidence"], key=CONF_RANK.get),
    }


def build_overlaps(*utilities):
    """Every cross-utility pair under the threshold, e.g. build_overlaps(desc, gpc, duke)."""
    overlaps = []
    for i, group_a in enumerate(utilities):
        for group_b in utilities[i + 1:]:
            for pa in group_a:
                for pb in group_b:
                    o = overlap_row(pa, pb)
                    if o:
                        overlaps.append(o)
    overlaps.sort(key=lambda o: -o["score"])
    for i, o in enumerate(overlaps, 1):
        o["rank"] = i
        o["overlap_id"] = f"OVL_{i}"
    return overlaps


def check_against_organizer(desc, gpc, overlaps):
    """Regression test: every organizer example overlap must be reproduced."""
    import openpyxl
    wb = openpyxl.load_workbook(ORGANIZER_XLSX, data_only=False)
    key = lambda t: re.sub(r"[^a-z0-9]", "", t.lower())
    by_key = {key(o["project_a_title"]) + "|" + key(o["project_b_title"]): o for o in overlaps}
    results = []
    for row in wb["overlaps"].iter_rows(min_row=2, values_only=True):
        ovl_id, dist, gap, _, _, name_a, _, _, name_b = row[:9]
        if not ovl_id:
            continue
        # first matching DESC twin wins (6809 E/G share a title)
        hits = [o for k, o in by_key.items() if k.startswith(key(name_a)[:25]) and k.endswith(key(name_b))]
        ours = min(hits, key=lambda o: o["distance_mi"]) if hits else None
        results.append({
            "organizer_id": ovl_id, "project_a": name_a, "project_b": name_b,
            "organizer_distance_mi": dist, "organizer_day_gap": gap,
            "our_overlap_id": ours and ours["overlap_id"],
            "our_distance_mi": ours and ours["distance_mi"],
            "our_day_gap": ours and ours["day_gap"],
            "reproduced": ours is not None,
        })
    return results


# ------------------------------------------------------------------- writers

def endpoint_cols(p, i):
    eps = route_ends(p["endpoints"])  # same two sub-points the center is computed from
    if i >= len(eps):
        return None, None, None, None
    e = eps[i]
    return e["name"], e["pt"][0] if e["pt"] else None, e["pt"][1] if e["pt"] else None, e["confidence"]


def write_xlsx(projects, overlaps, regression, path):
    import openpyxl
    from openpyxl.styles import Font, PatternFill

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "projects"
    head = ["project_id", "utility", "state", "project_name", "name_a", "lat_a", "lon_a", "name_b", "lat_b",
            "lon_b", "lat_center", "lon_center", "in_service_date", "overlap_count", "overlap_1", "overlap_2",
            "overlap_3", "confidence", "conf_a", "conf_b", "source_id", "zone", "total_cost_usd", "notes"]
    ws.append(head)
    partners = {}
    for o in overlaps:
        partners.setdefault(o["project_id_a"], []).append(o["project_id_b"])
        partners.setdefault(o["project_id_b"], []).append(o["project_id_a"])
    for r, p in enumerate(projects, 2):
        na, la, oa, ca = endpoint_cols(p, 0)
        nb, lb, ob, cb = endpoint_cols(p, 1)
        mine = partners.get(p["project_id"], [])
        notes = p["data_quality_flags"] + (p["geo"]["notes"] if p["geo"] else ["no endpoint located"])
        ws.append([
            p["project_id"], p["utility"], p["state"], p["title"], na, la, oa, nb, lb, ob,
            f"=IF(ISBLANK(I{r}), F{r}, IF(ISBLANK(F{r}), I{r}, (F{r}+I{r})/2))",
            f"=IF(ISBLANK(J{r}), G{r}, IF(ISBLANK(G{r}), J{r}, (G{r}+J{r})/2))",
            p["in_service_date"] or p["in_service_year"], len(mine), *(mine + [None] * 3)[:3],
            p["geo"]["confidence"] if p["geo"] else "unlocated", ca, cb,
            p.get("source_project_id") or p.get("teams_number"), p.get("zone"), p.get("total_cost_usd"),
            " | ".join(notes),
        ])

    ws = wb.create_sheet("overlaps")
    ws.append(["overlap_id", "distance_mi", "time_gap (day)", "utility_a", "project_id_a", "project_name_a",
               "utility_b", "project_id_b", "project_name_b", "rank", "score", "confidence", "opportunity",
               "shared_stations"])
    for o in overlaps:
        ws.append([o["overlap_id"], o["distance_mi"], o["day_gap"], o["utility_a"], o["project_id_a"],
                   o["project_a_title"], o["utility_b"], o["project_id_b"], o["project_b_title"], o["rank"],
                   o["score"], o["confidence"], o["tier"], " | ".join(o["shared_stations"])])

    ws = wb.create_sheet("endpoint_validation")
    ws.append(["project_id", "project_name", "endpoint", "confidence", "lat", "lon", "source", "name_score",
               "operator_ok", "zone_km", "osm_vs_organizer_km", "notes"])
    fills = {"confirmed": "D9F2D9", "low_confidence": "FFF2CC", "rejected": "F8CBAD", "unlocated": "EDEDED"}
    for p in projects:
        for e in p["endpoints"]:
            c = e["checks"] or {}
            ws.append([p["project_id"], p["title"], e["name"], e["confidence"],
                       e["pt"][0] if e["pt"] else None, e["pt"][1] if e["pt"] else None,
                       e["source"] or e.get("rejected_source"), c.get("name_score"), c.get("operator_ok"),
                       c.get("zone_km"), c.get("osm_agrees_km"), " | ".join(e["notes"])])
            if e["confidence"] in fills:
                ws.cell(ws.max_row, 4).fill = PatternFill("solid", fgColor=fills[e["confidence"]])

    ws = wb.create_sheet("data_quality")
    ws.append(["project_id", "project_name", "issue"])
    for p in projects:
        for f in p["data_quality_flags"]:
            ws.append([p["project_id"], p["title"], f])

    ws = wb.create_sheet("organizer_check")
    ws.append(list(regression[0].keys()) if regression else ["no organizer rows"])
    for r in regression:
        ws.append(list(r.values()))

    for sheet in wb:
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        sheet.freeze_panes = "A2"
    wb.save(path)


def write_geojson(projects, path):
    feats = []
    for p in projects:
        if not p["geo"]:
            continue
        props = {k: p.get(k) for k in ("project_id", "utility", "title", "in_service_date", "zone",
                                       "total_cost_usd", "source_project_id", "teams_number")}
        props["confidence"] = p["geo"]["confidence"]
        pts = p["geo"]["points"]
        if len(pts) > 1:
            feats.append({"type": "Feature", "properties": {**props, "role": "line"},
                          "geometry": {"type": "LineString", "coordinates": [[q[1], q[0]] for q in pts]}})
        c = p["geo"]["center"]
        feats.append({"type": "Feature", "properties": {**props, "role": "center"},
                      "geometry": {"type": "Point", "coordinates": [c[1], c[0]]}})
    json.dump({"type": "FeatureCollection", "features": feats}, open(path, "w"), indent=1)


def write_csvs(projects, overlaps):
    with open(CLEAN / "overlaps.csv", "w", newline="") as f:
        cols = ["overlap_id", "rank", "score", "distance_mi", "day_gap", "tier", "confidence", "project_id_a",
                "project_a_title", "project_id_b", "project_b_title"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(overlaps)
    with open(CLEAN / "projects.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["project_id", "utility", "title", "in_service_date", "lat_center", "lon_center", "confidence"])
        for p in projects:
            c = p["geo"]["center"] if p["geo"] else (None, None)
            w.writerow([p["project_id"], p["utility"], p["title"], p["in_service_date"] or p["in_service_year"], *c,
                        p["geo"]["confidence"] if p["geo"] else "unlocated"])


# ---------------------------------------------------------------------- main

def summarize(projects):
    from collections import Counter
    proj = Counter(p["geo"]["confidence"] if p["geo"] else "unlocated" for p in projects)
    eps = Counter(e["confidence"] for p in projects for e in p["endpoints"])
    return {"projects": dict(proj), "endpoints": dict(eps)}


def main():
    desc, gpc, duke, dropped = build_projects()
    overlaps = build_overlaps(desc, gpc, duke)
    regression = check_against_organizer(desc, gpc, overlaps)
    summary = {
        "desc": summarize(desc),
        "gpc": summarize(gpc),
        "duke": summarize(duke),
        "gpc_rows_dropped_other_sponsors": dropped,
        "threshold_mi": THRESHOLD_MI,
        "scoring": {"w_distance": W_DIST, "w_time": W_TIME, "max_gap_days": MAX_GAP_DAYS},
        "overlaps": len(overlaps),
        "overlaps_confirmed": sum(o["confidence"] == "confirmed" for o in overlaps),
        "organizer_reproduced": f"{sum(r['reproduced'] for r in regression)}/{len(regression)}",
    }
    out = {"summary": summary, "organizer_check": regression,
           "desc_projects": desc, "gpc_projects": gpc, "duke_projects": duke, "overlaps": overlaps}
    json.dump(out, open(CLEAN / "sentinel_dataset.json", "w"), indent=1)
    write_xlsx(desc + gpc + duke, overlaps, regression, CLEAN / "Projects_Overlaps.xlsx")
    write_geojson(desc, CLEAN / "desc_projects.geojson")
    write_geojson(gpc, CLEAN / "gpc_projects.geojson")
    write_geojson(duke, CLEAN / "duke_projects.geojson")
    write_csvs(desc + gpc + duke, overlaps)

    print(json.dumps(summary, indent=1))
    print("\nOrganizer worked example:")
    for r in regression:
        mark = "OK " if r["reproduced"] else "MISSING"
        print(f"  {mark} {r['organizer_id']}: {r['project_a'][:35]:35s} <-> {r['project_b'][:40]:40s} "
              f"organizer {r['organizer_distance_mi']} mi / {r['organizer_day_gap']} d   "
              f"ours {r['our_distance_mi']} mi / {r['our_day_gap']} d")
    print(f"\nTop overlaps (score = {W_DIST}*(1-dist/{THRESHOLD_MI:g}) + {W_TIME}*(1-min(gap,{MAX_GAP_DAYS})/{MAX_GAP_DAYS})):")
    for o in overlaps[:15]:
        print(f"  #{o['rank']:<3} {o['score']:.3f}  {o['distance_mi']:5.2f} mi  {str(o['day_gap']):>5} d  "
              f"{o['confidence']:14s} {o['project_a_title'][:38]:38s} <-> {o['project_b_title'][:45]}")


if __name__ == "__main__":
    main()
