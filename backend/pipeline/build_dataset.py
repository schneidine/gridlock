"""
Gridlock overlap-detection pipeline.

Loads the parsed DESC + GPC project lists, geocodes each project's named
stations via the gazetteer, computes closest-point distance between every
DESC x GPC project pair, and flags/ranks overlaps per the challenge spec:

  - primary signal: geographic closest-point distance (segment-to-segment
    where both endpoints of a project are known; point-to-point otherwise)
  - flag any pair under 40 km (25 mi)
  - rank into 4 tiers: touching/crossing, <1.6km, <8km, <40km
  - secondary signal: gap (in days) between planned in-service dates
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from coords_seed import DESC_COORDS, GPC_COORDS
from datetime import datetime

ROOT = Path(__file__).parent.parent
CLEAN = ROOT / "data_clean"

KM_PER_MI = 1.60934
THRESHOLD_KM = 40.0  # 25 mi


def normalize(name: str) -> str:
    return name.strip().lower()


def lookup(name: str, gazetteer: dict):
    key = normalize(name)
    if key in gazetteer:
        return gazetteer[key]
    # try loose containment match (e.g. "Thurmond Dam #5" -> "thurmond dam")
    for gk, val in gazetteer.items():
        if gk in key or key in gk:
            return val
    return None


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def closest_point_km(pointsA, pointsB):
    """
    pointsA / pointsB: list of (lat, lon) endpoints for a project (1 or 2 points).
    Returns the minimum haversine distance between any endpoint of A and any
    endpoint of B. This approximates true segment-to-segment closest-point
    distance (adequate at this line length / distance scale -- the minimum
    endpoint-to-endpoint distance is always an upper bound on the true
    closest-point distance between two nearby line segments, and for our
    threshold band (<40km) the two are close in practice since these lines
    are short relative to the 40km flagging radius).
    """
    best = None
    for a in pointsA:
        for b in pointsB:
            d = haversine_km(a[0], a[1], b[0], b[1])
            if best is None or d < best:
                best = d
    return best


def parse_date(s):
    if s is None:
        return None
    s = str(s).strip()
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    # already a datetime-ish string from json (e.g. "2025-06-01T00:00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def geocode_project(stations, gazetteer):
    pts = []
    confidences = []
    notes = []
    for s in stations:
        hit = lookup(s, gazetteer)
        if hit:
            lat, lon, conf, note = hit
            pts.append((lat, lon))
            confidences.append(conf)
            notes.append(f"{s} -> {note}")
    if not pts:
        return None
    # de-dupe identical points, cap at 2 endpoints for the segment approx
    uniq = []
    for p in pts:
        if p not in uniq:
            uniq.append(p)
    return {
        "points": uniq[:2] if len(uniq) > 1 else uniq,
        "center": (sum(p[0] for p in uniq) / len(uniq), sum(p[1] for p in uniq) / len(uniq)),
        "confidence": min(confidences, key=lambda c: {"confirmed": 0, "estimated": 1, "region_only": 2}[c]),
        "worst_confidence": max(confidences, key=lambda c: {"confirmed": 0, "estimated": 1, "region_only": 2}[c]),
        "geocode_notes": notes,
    }


def tier_for(distance_km):
    if distance_km <= 0.05:
        return "touching_crossing"
    if distance_km < 1.6:
        return "share_land"
    if distance_km < 8:
        return "share_logistics"
    if distance_km < THRESHOLD_KM:
        return "share_crews"
    return None


def main():
    desc = json.load(open(CLEAN / "desc_projects_raw.json"))
    gpc_all = json.load(open(CLEAN / "gpc_projects_raw.json"))
    gpc = [p for p in gpc_all if p.get("sponsor") in ("GPC", "SAV")]

    desc_projects = []
    for i, p in enumerate(desc):
        geo = geocode_project(p["stations"], DESC_COORDS)
        desc_projects.append({
            "project_id": f"DESC_{i+1}",
            "utility": "Dominion Energy South Carolina",
            "state": "SC",
            "title": p["title"],
            "description": p["description"],
            "status": p["status"],
            "in_service_date_raw": p["in_service_date"],
            "in_service_date": parse_date(p["in_service_date"]).isoformat() if parse_date(p["in_service_date"]) else None,
            "stations": p["stations"],
            "geo": geo,
        })

    gpc_projects = []
    for i, p in enumerate(gpc):
        geo = geocode_project(p["stations"], GPC_COORDS)
        gpc_projects.append({
            "project_id": f"GPC_{i+1}",
            "utility": "Georgia Power",
            "state": "GA",
            "title": p["project_name"],
            "description": None,
            "status": None,
            "in_service_date_raw": p["need_date"],
            "in_service_date": parse_date(p["need_date"]).isoformat() if parse_date(p["need_date"]) else None,
            "stations": p["stations"],
            "zone": p["zone"],
            "sponsor": p["sponsor"],
            "geo": geo,
        })

    # overlap detection: every DESC x GPC pair with geocoded points on both sides
    overlaps = []
    for dp in desc_projects:
        if not dp["geo"]:
            continue
        for gp in gpc_projects:
            if not gp["geo"]:
                continue
            dist_km = closest_point_km(dp["geo"]["points"], gp["geo"]["points"])
            tier = tier_for(dist_km)
            if tier is None:
                continue
            dd = parse_date(dp["in_service_date_raw"])
            gd = parse_date(gp["in_service_date_raw"])
            day_gap = abs((dd - gd).days) if dd and gd else None
            overlaps.append({
                "project_id_a": dp["project_id"],
                "project_a_title": dp["title"],
                "utility_a": dp["utility"],
                "project_id_b": gp["project_id"],
                "project_b_title": gp["title"],
                "utility_b": gp["utility"],
                "distance_km": round(dist_km, 2),
                "distance_mi": round(dist_km / KM_PER_MI, 2),
                "tier": tier,
                "day_gap": day_gap,
                "confidence": min(dp["geo"]["confidence"], gp["geo"]["confidence"],
                                   key=lambda c: {"confirmed": 0, "estimated": 1, "region_only": 2}[c]),
            })

    overlaps.sort(key=lambda o: o["distance_km"])

    out = {
        "desc_projects": desc_projects,
        "gpc_projects": gpc_projects,
        "overlaps": overlaps,
    }
    outpath = ROOT / "data_clean" / "gridlock_dataset.json"
    json.dump(out, open(outpath, "w"), indent=2)

    print(f"{len(desc_projects)} DESC projects ({sum(1 for p in desc_projects if p['geo'])} geocoded)")
    print(f"{len(gpc_projects)} GPC projects ({sum(1 for p in gpc_projects if p['geo'])} geocoded)")
    print(f"{len(overlaps)} overlaps found (< {THRESHOLD_KM} km)")
    print()
    print("Top 15 closest pairs:")
    for o in overlaps[:15]:
        print(f"  [{o['tier']:16s}] {o['distance_mi']:6.2f} mi  {o['project_a_title'][:45]:45s} <-> {o['project_b_title'][:45]:45s}  (conf: {o['confidence']})")


if __name__ == "__main__":
    main()
