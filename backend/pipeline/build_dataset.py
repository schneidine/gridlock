"""
Gridlock overlap-detection pipeline.

Loads the parsed DESC + GPC project lists, geocodes every named endpoint
against OpenStreetMap (pipeline/geocode.py, with validation + confidence
flags), and builds the overlap table exactly as the challenge defines it:

  - center point = midpoint of the located endpoints (one point -> that point)
  - haversine distance between every DESC center and every GPC center
  - every pair under 25 miles is one overlap row, with the in-service day gap
  - ranked by score = 0.7 * (1 - dist/25) + 0.3 * (1 - min(gap, 1825)/1825)

Outputs (data_clean/):
  gridlock_dataset.json        what the web UI reads
  Projects_Overlaps.xlsx       projects / overlaps sheets in the organizer's format,
                               plus endpoint_validation and data_quality sheets
  projects.csv, overlaps.csv
  desc_projects.geojson, gpc_projects.geojson
"""
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from geocode import Geocoder, geocode_project, haversine_km

ROOT = Path(__file__).parent.parent
CLEAN = ROOT / "data_clean"
ORGANIZER_XLSX = ROOT / "data_raw" / "challenge-brief" / "Projects_Overlaps_organizer_example.xlsx"

KM_PER_MI = 1.609344
THRESHOLD_MI = 25.0
MAX_GAP_DAYS = 1825  # 5 years: beyond this, timing no longer helps coordination
W_DIST, W_TIME = 0.7, 0.3
KEEP_SPONSORS = ("GPC", "SAV")  # SAV = Georgia Power's Savannah division
CONF_RANK = {"confirmed": 0, "low_confidence": 1}


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


def tier_for(dist_km):
    """Distance tier the frontend/Supabase schema expects (overlaps.tier is NOT NULL)."""
    if dist_km <= 0.05:
        return "touching_crossing"
    if dist_km < 1.6:
        return "share_land"
    if dist_km < 8:
        return "share_logistics"
    return "share_crews"


def score(dist_mi, gap_days):
    gap = MAX_GAP_DAYS if gap_days is None else min(gap_days, MAX_GAP_DAYS)
    return round(W_DIST * (1 - dist_mi / THRESHOLD_MI) + W_TIME * (1 - gap / MAX_GAP_DAYS), 4)


def date_note(raw, parsed):
    if parsed is None:
        return f"unparseable in-service date '{raw}'"
    if not re.fullmatch(r"\s*\d{1,2}/\d{1,2}/\d{2,4}\s*", str(raw)):
        return f"in-service date '{raw}' has extra text; used first date {parsed:%Y-%m-%d}"
    return None


def make_project(pid, utility, state, title, raw_date, stations, geo, **extra):
    d = parse_date(raw_date)
    notes = list(extra.pop("data_quality_flags", []))
    if date_note(raw_date, d):
        notes.append(date_note(raw_date, d))
    located = [e for e in geo["endpoints"] if e["pt"]]
    return {
        "project_id": pid,
        "utility": utility,
        "state": state,
        "title": title,
        "in_service_date_raw": raw_date,
        "in_service_date": d.date().isoformat() if d else None,
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

    geocoder = Geocoder()
    anchors = geocoder.build_zone_centroids(gpc_raw)
    print(f"OSM: {len(geocoder.osm)} named substations in GA/SC")
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
    geocoder.nom.save()
    return desc, gpc, len(gpc_all) - len(gpc_raw)


def build_overlaps(desc, gpc):
    overlaps = []
    for dp in desc:
        if not dp["geo"]:
            continue
        for gp in gpc:
            if not gp["geo"]:
                continue
            dist_mi = haversine_km(dp["geo"]["center"], gp["geo"]["center"]) / KM_PER_MI
            if dist_mi >= THRESHOLD_MI:
                continue
            dd, gd = parse_date(dp["in_service_date_raw"]), parse_date(gp["in_service_date_raw"])
            gap = abs((dd - gd).days) if dd and gd else None
            conf = max(dp["geo"]["confidence"], gp["geo"]["confidence"], key=CONF_RANK.get)
            overlaps.append({
                "project_id_a": dp["project_id"], "project_a_title": dp["title"], "utility_a": dp["utility"],
                "project_id_b": gp["project_id"], "project_b_title": gp["title"], "utility_b": gp["utility"],
                "distance_mi": round(dist_mi, 2),
                "distance_km": round(dist_mi * KM_PER_MI, 2),
                "tier": tier_for(dist_mi * KM_PER_MI),
                "day_gap": gap,
                "score": score(dist_mi, gap),
                "confidence": conf,
            })
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
    eps = [e for e in p["endpoints"] if e["confidence"] != "not_a_place"]
    if i >= len(eps):
        return None, None, None, None
    e = eps[i]
    return e["name"], e["pt"][0] if e["pt"] else None, e["pt"][1] if e["pt"] else None, e["confidence"]


def write_xlsx(desc, gpc, overlaps, regression, path):
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
    for r, p in enumerate(desc + gpc, 2):
        na, la, oa, ca = endpoint_cols(p, 0)
        nb, lb, ob, cb = endpoint_cols(p, 1)
        mine = partners.get(p["project_id"], [])
        notes = p["data_quality_flags"] + (p["geo"]["notes"] if p["geo"] else ["no endpoint located"])
        ws.append([
            p["project_id"], p["utility"], p["state"], p["title"], na, la, oa, nb, lb, ob,
            f"=IF(ISBLANK(I{r}), F{r}, IF(ISBLANK(F{r}), I{r}, (F{r}+I{r})/2))",
            f"=IF(ISBLANK(J{r}), G{r}, IF(ISBLANK(G{r}), J{r}, (G{r}+J{r})/2))",
            p["in_service_date"], len(mine), *(mine + [None] * 3)[:3],
            p["geo"]["confidence"] if p["geo"] else "unlocated", ca, cb,
            p.get("source_project_id") or p.get("teams_number"), p.get("zone"), p.get("total_cost_usd"),
            " | ".join(notes),
        ])

    ws = wb.create_sheet("overlaps")
    ws.append(["overlap_id", "distance_mi", "time_gap (day)", "utility_a", "project_id_a", "project_name_a",
               "utility_b", "project_id_b", "project_name_b", "rank", "score", "confidence"])
    for o in overlaps:
        ws.append([o["overlap_id"], o["distance_mi"], o["day_gap"], o["utility_a"], o["project_id_a"],
                   o["project_a_title"], o["utility_b"], o["project_id_b"], o["project_b_title"], o["rank"],
                   o["score"], o["confidence"]])

    ws = wb.create_sheet("endpoint_validation")
    ws.append(["project_id", "project_name", "endpoint", "confidence", "lat", "lon", "source", "name_score",
               "operator_ok", "zone_km", "osm_vs_organizer_km", "notes"])
    fills = {"confirmed": "D9F2D9", "low_confidence": "FFF2CC", "rejected": "F8CBAD", "unlocated": "EDEDED"}
    for p in desc + gpc:
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
    for p in desc + gpc:
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


def write_csvs(desc, gpc, overlaps):
    with open(CLEAN / "overlaps.csv", "w", newline="") as f:
        cols = ["overlap_id", "rank", "score", "distance_mi", "day_gap", "confidence", "project_id_a",
                "project_a_title", "project_id_b", "project_b_title"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(overlaps)
    with open(CLEAN / "projects.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["project_id", "utility", "title", "in_service_date", "lat_center", "lon_center", "confidence"])
        for p in desc + gpc:
            c = p["geo"]["center"] if p["geo"] else (None, None)
            w.writerow([p["project_id"], p["utility"], p["title"], p["in_service_date"], *c,
                        p["geo"]["confidence"] if p["geo"] else "unlocated"])


# ---------------------------------------------------------------------- main

def summarize(projects):
    from collections import Counter
    proj = Counter(p["geo"]["confidence"] if p["geo"] else "unlocated" for p in projects)
    eps = Counter(e["confidence"] for p in projects for e in p["endpoints"])
    return {"projects": dict(proj), "endpoints": dict(eps)}


def main():
    desc, gpc, dropped = build_projects()
    overlaps = build_overlaps(desc, gpc)
    regression = check_against_organizer(desc, gpc, overlaps)
    summary = {
        "desc": summarize(desc),
        "gpc": summarize(gpc),
        "gpc_rows_dropped_other_sponsors": dropped,
        "threshold_mi": THRESHOLD_MI,
        "scoring": {"w_distance": W_DIST, "w_time": W_TIME, "max_gap_days": MAX_GAP_DAYS},
        "overlaps": len(overlaps),
        "overlaps_confirmed": sum(o["confidence"] == "confirmed" for o in overlaps),
        "organizer_reproduced": f"{sum(r['reproduced'] for r in regression)}/{len(regression)}",
    }
    out = {"summary": summary, "organizer_check": regression,
           "desc_projects": desc, "gpc_projects": gpc, "overlaps": overlaps}
    json.dump(out, open(CLEAN / "gridlock_dataset.json", "w"), indent=1)
    write_xlsx(desc, gpc, overlaps, regression, CLEAN / "Projects_Overlaps.xlsx")
    write_geojson(desc, CLEAN / "desc_projects.geojson")
    write_geojson(gpc, CLEAN / "gpc_projects.geojson")
    write_csvs(desc, gpc, overlaps)

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
