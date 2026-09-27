"""
Geocode project endpoints against OpenStreetMap, with validation.

Pipeline for every named endpoint (substation) in a project title:

  1. Organizer worked example -- if the challenge's Projects_Overlaps.xlsx
     already pins this station, use it (ground truth) and record how far our
     own OSM match lands from it as a cross-check.
  2. OSM substations -- one Overpass pull of every named power=substation in
     GA/SC (cached under data_raw/osm/), fuzzy-matched with rapidfuzz on
     normalized names, filtered to the right utility's operators and state.
  3. Nominatim fallback -- the town/place the station is named after, always
     low-confidence.

Then each match is validated:

  - name score        exact-ish (>= 95) vs fuzzy (88-95)
  - operator          OSM operator tag belongs to the right utility
  - ambiguity         several same-named substations -> pick by context and say so
  - zone (GPC)        match must sit near the other confirmed stations in the
                      same GPC planning zone (the "same name, wrong county" trap)
  - state box (DESC)  match must be in/adjacent to South Carolina
  - endpoint span     both ends of one line should be within LINE_SPAN_KM

A match that fails zone/state is REJECTED (endpoint left unlocated) rather than
kept; everything else gets `confirmed` or `low_confidence`. Every decision is
written to the endpoint's `checks` / `notes` so the UI and xlsx can show why.
"""
import json
import math
import re
import statistics
import time
from pathlib import Path

import requests
from rapidfuzz import fuzz

ROOT = Path(__file__).parent.parent
OSM_DIR = ROOT / "data_raw" / "osm"
OVERPASS_CACHE = OSM_DIR / "overpass_substations_ga_sc.json"
NOMINATIM_CACHE = OSM_DIR / "nominatim_cache.json"

BBOX = (30.3, -85.7, 35.3, -78.5)  # GA + SC
OVERPASS_QUERY = f'[out:json][timeout:120];nwr["power"="substation"]["name"]{BBOX};out center tags;'
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
USER_AGENT = "sentinel-utilities-shellhacks/1.0 (hackathon project)"

STRONG, FUZZY = 95, 88
ZONE_KM = 90          # min allowed distance from a GPC zone's anchor centroid
ZONE_KM_MAX = 200     # zones grow with their anchors' spread, up to this
LINE_SPAN_KM = 160    # max plausible distance between two ends of one line
SAME_PLACE_KM = 2

UTILITY_OPERATORS = {
    "DESC": ("dominion", "south carolina electric", "south carolina gas", "sce&g", "scana"),
    "GPC": ("georgia power",),
}
# DESC is an SC utility, but its tie lines end at GA substations along the river
DESC_BOX = (31.9, -83.5, 35.3, -78.5)
GPC_BOX = (30.3, -85.7, 35.05, -80.8)

# Organizer worked example (Projects_Overlaps.xlsx) -- treated as ground truth.
ORGANIZER = {
    "DESC": {
        "stevens creek": (33.562599, -82.051362),
        "thurmond": (33.660127, -82.195931),
        "jasper": (32.35912, -81.1246),
        "okatie": (32.333758, -81.032495),
        "queensboro": (32.722793, -79.967332),
        "bluffton": (32.235027, -80.853384),
    },
    "GPC": {
        "evans": (33.543994, -82.168648),
        "thurmond": (33.660127, -82.195931),
        "mcintosh": (32.352116, -81.175112),
        "goshen sav": (32.248701, -81.209472),
        "mitchell": (31.447121, -84.133843),
        "north tifton": (31.478089, -83.549130),
        "jesup": (31.603106, -81.924947),
        "ludowici": (31.721597, -81.743703),
    },
}

# Title fragments that are scope words, not places
NOISE = [
    r"switching station", r"substation", r"\bsub\b", r"\bprimary\b", r"\bpri\b",
    r"\bdam\b", r"\busa\b", r"relay modernization", r"\brelay\b", r"bank replacement",
    r"bank [a-z] replacement", r"\bbank\b", r"new auto transformer", r"auto ?transformer",
    r"reactors? (installation|removal)", r"\breactors?\b", r"statcom system", r"\bstatcom\b",
    r"cap bank", r"\bbuses\b.*", r"\bbus\b.*", r"area improvements", r"\bimprovements?\b",
    r"\bupgrades?\b", r"\bequipment\b", r"\breplacement\b", r"\bnew build\b", r"\bnew\b",
    r"\bsecond transformer\b", r"\btransmission\b", r"\bpower\b", r"\belectric\b",
    r"\bplant\b", r"\bstation\b", r"\bjct\b", r"\bjunction\b", r"\blow side breaker\b",
    r"\bbreaker\b.*", r"\bstrategic\b.*", r"\barea\b",
]
# Endpoints that are not places at all (customer-connection prefixes, programs)
NOT_A_PLACE = re.compile(
    r"^(cc|cc improvements?|grid|lg|smart valve.*|project .*|.*network improvements.*|"
    r".*data network.*|.* transmission needs|.*customer sub.*)$"
)
PLACE_TYPES = {"city", "town", "village", "hamlet", "suburb", "neighbourhood", "quarter", "locality"}


def normalize(name: str) -> str:
    s = name.lower().replace("&", " ")
    s = re.sub(r"[\x00-\x1f]", "", s)
    s = re.sub(r"\((sav)\)", r" \1 ", s)          # keep the Savannah-division marker
    s = re.sub(r"\([^)]*\)", " ", s)              # drop other parentheticals: (USA), (APC), (WHITE)
    s = re.sub(r"#\s*\d+", " ", s)
    s = re.sub(r"\b\d+\s*/?\s*\d*\s*kv\b", " ", s)
    s = re.sub(r"\b\d+(/\d+)?\b", " ", s)
    for pat in NOISE:
        s = re.sub(pat, " ", s)
    s = re.sub(r"\bst\b\.?", "st", s)
    s = re.sub(r"\bft\b\.?", "fort", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def haversine_km(a, b):
    R = 6371.0088
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dphi, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def in_box(pt, box):
    return box[0] <= pt[0] <= box[2] and box[1] <= pt[1] <= box[3]


# Coarse Georgia outline (lat, lon); the east edge follows the Chattooga /
# Tugaloo / Savannah River border with SC, which is exactly where overlaps live.
GA_OUTLINE = [
    (35.00, -85.61), (35.00, -83.11), (34.83, -83.32), (34.49, -83.05), (34.36, -82.82),
    (34.02, -82.59), (33.66, -82.20), (33.47, -81.94), (33.30, -81.80), (32.94, -81.50),
    (32.53, -81.27), (32.35, -81.14), (32.08, -81.09), (32.03, -80.85), (31.00, -81.40),
    (30.71, -81.45), (30.36, -82.05), (30.71, -84.86), (31.00, -85.00), (32.00, -85.06),
    (32.85, -85.18),
]


def in_georgia(pt):
    lat, lon = pt
    inside = False
    for (a_lat, a_lon), (b_lat, b_lon) in zip(GA_OUTLINE, GA_OUTLINE[1:] + GA_OUTLINE[:1]):
        if (a_lat > lat) != (b_lat > lat):
            if lon < a_lon + (lat - a_lat) * (b_lon - a_lon) / (b_lat - a_lat):
                inside = not inside
    return inside


RIVER_BORDER = GA_OUTLINE[1:14]  # NE corner down to the Savannah River mouth
BORDER_TOLERANCE_KM = 5          # the outline is coarse; river-bank stations sit on it


def km_to_border(pt):
    """Approximate distance to the GA/SC river border (equirectangular, fine at this scale)."""
    kx = 111.32 * math.cos(math.radians(pt[0]))
    best = float("inf")
    for (a_lat, a_lon), (b_lat, b_lon) in zip(RIVER_BORDER, RIVER_BORDER[1:]):
        ax, ay = (a_lon - pt[1]) * kx, (a_lat - pt[0]) * 110.57
        bx, by = (b_lon - pt[1]) * kx, (b_lat - pt[0]) * 110.57
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best


def state_ok(pt, utility, operator_ok):
    """GPC stations are in Georgia; DESC stations are in SC, except tie-line ends."""
    on_border = km_to_border(pt) <= BORDER_TOLERANCE_KM
    if utility == "GPC":
        return in_box(pt, GPC_BOX) and (in_georgia(pt) or operator_ok or on_border)
    return in_box(pt, DESC_BOX) and (not in_georgia(pt) or operator_ok or on_border)


# ---------------------------------------------------------------- data sources

def load_osm_substations():
    if not OVERPASS_CACHE.exists():
        OSM_DIR.mkdir(parents=True, exist_ok=True)
        for url in OVERPASS_MIRRORS:
            try:
                r = requests.post(url, data={"data": OVERPASS_QUERY},
                                  headers={"User-Agent": USER_AGENT}, timeout=180)
                if r.ok and r.text.lstrip().startswith("{"):
                    OVERPASS_CACHE.write_text(r.text)
                    break
            except requests.RequestException:
                continue
        else:
            raise RuntimeError("every Overpass mirror failed; retry later")
    feats = []
    for e in json.loads(OVERPASS_CACHE.read_text())["elements"]:
        tags = e.get("tags", {})
        lat = e.get("lat", e.get("center", {}).get("lat"))
        lon = e.get("lon", e.get("center", {}).get("lon"))
        if lat is None or not tags.get("name"):
            continue
        feats.append({
            "osm_id": f"{e['type']}/{e['id']}",
            "name": tags["name"],
            "norm": normalize(tags["name"]),
            "operator": tags.get("operator") or "",
            "voltage": tags.get("voltage"),
            "pt": (lat, lon),
        })
    return feats


class Nominatim:
    def __init__(self):
        self.cache = json.loads(NOMINATIM_CACHE.read_text()) if NOMINATIM_CACHE.exists() else {}
        self.last = 0.0

    def search(self, q):
        if q not in self.cache:
            wait = 1.1 - (time.time() - self.last)
            if wait > 0:
                time.sleep(wait)
            try:
                r = requests.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": q, "format": "jsonv2", "countrycodes": "us", "limit": 5},
                    headers={"User-Agent": USER_AGENT}, timeout=30,
                )
                self.cache[q] = r.json() if r.ok else []
            except requests.RequestException:
                return []  # don't cache transient failures
            self.last = time.time()
        return self.cache[q]

    def save(self):
        OSM_DIR.mkdir(parents=True, exist_ok=True)
        NOMINATIM_CACHE.write_text(json.dumps(self.cache, indent=1))


# ---------------------------------------------------------------- matching

class Geocoder:
    def __init__(self):
        self.osm = load_osm_substations()
        self.nom = Nominatim()
        self.zone_centroids = {}
        self.zone_radius = {}

    def osm_candidates(self, norm, utility):
        box = DESC_BOX if utility == "DESC" else GPC_BOX
        ops = UTILITY_OPERATORS[utility]
        out = []
        for f in self.osm:
            if not in_box(f["pt"], box):
                continue
            score = fuzz.ratio(norm, f["norm"])
            if score < FUZZY:
                continue
            op = f["operator"].lower()
            op_ok = any(o in op for o in ops)
            tie_end = utility == "DESC" and "georgia power" in op
            # DESC tie lines legitimately end at Georgia Power stations; anything
            # else tagged with a third utility is somebody else's substation.
            if op and not op_ok and not tie_end:
                continue
            if not state_ok(f["pt"], utility, op_ok or tie_end):
                continue
            out.append({**f, "score": score, "operator_ok": op_ok})
        out.sort(key=lambda c: (-c["score"], not c["operator_ok"]))
        return out

    def locate(self, raw_name, utility, zone=None, anchor=None):
        """Return an endpoint dict (always), with pt=None when unlocated."""
        norm = normalize(raw_name)
        ep = {"name": raw_name, "norm": norm, "pt": None, "source": None,
              "confidence": None, "checks": {}, "notes": []}
        if not norm or NOT_A_PLACE.match(norm):
            ep["notes"].append("not a place name (customer-connection / program label) -- skipped")
            ep["confidence"] = "not_a_place"
            return ep

        cands = self.osm_candidates(re.sub(r" sav$", "", norm), utility)
        best_osm = None
        if cands:
            # collapse candidates that are the same physical site
            sites = []
            for c in cands:
                if c["score"] < cands[0]["score"] - 3:
                    break
                if all(haversine_km(c["pt"], s["pt"]) > SAME_PLACE_KM for s in sites):
                    sites.append(c)
            best_osm = sites[0]
            if len(sites) > 1:
                ref = self.zone_centroids.get(zone) if utility == "GPC" else anchor
                if ref:
                    best_osm = min(sites, key=lambda s: haversine_km(s["pt"], ref))
                    ep["notes"].append(
                        f"{len(sites)} OSM substations named like '{raw_name}' "
                        f"({', '.join(f'{s['pt'][0]:.2f},{s['pt'][1]:.2f}' for s in sites)}); "
                        f"picked the one nearest the {'zone ' + str(zone) if utility == 'GPC' else 'other endpoint'}"
                    )
                    ep["checks"]["ambiguous_resolved"] = True
                else:
                    ep["notes"].append(f"{len(sites)} same-named OSM substations and no context to choose")
                    ep["checks"]["ambiguous_resolved"] = False

        org = ORGANIZER[utility].get(norm)
        if org:
            ep.update(pt=org, source="organizer worked example")
            ep["checks"]["organizer"] = True
            if best_osm:
                d = haversine_km(org, best_osm["pt"])
                ep["checks"]["osm_agrees_km"] = round(d, 2)
                ep["notes"].append(f"OSM '{best_osm['name']}' ({best_osm['osm_id']}) lands {d:.2f} km from the organizer point")
        elif best_osm:
            ep.update(pt=best_osm["pt"], source=f"OSM {best_osm['osm_id']} '{best_osm['name']}'"
                      f" [{best_osm['operator'] or 'no operator tag'}]")
            ep["checks"]["name_score"] = round(best_osm["score"])
            ep["checks"]["operator_ok"] = best_osm["operator_ok"]
            ep["checks"]["operator_tagged"] = bool(best_osm["operator"])
            ep["checks"]["unique_site"] = len(sites) == 1
            ep["osm_id"] = best_osm["osm_id"]
        else:
            self._nominatim(ep, norm, utility)

        self._validate(ep, utility, zone)
        return ep

    def _nominatim(self, ep, norm, utility):
        state = "South Carolina" if utility == "DESC" else "Georgia"
        box = DESC_BOX if utility == "DESC" else GPC_BOX
        for q, kind in ((f"{norm} substation, {state}", "power"), (f"{norm}, {state}", "place")):
            for r in self.nom.search(q):
                pt = (float(r["lat"]), float(r["lon"]))
                if not state_ok(pt, utility, False):
                    continue
                if kind == "power" and r.get("category") != "power":
                    continue
                if kind == "place" and r.get("addresstype", r.get("type")) not in PLACE_TYPES:
                    continue
                score = fuzz.ratio(norm, normalize(r.get("name", "")))
                if score < FUZZY:
                    continue
                ep.update(pt=pt, source=f"Nominatim {kind}: {r.get('display_name', '')[:80]}")
                ep["checks"]["name_score"] = round(score)
                ep["checks"]["town_centroid"] = kind == "place"
                if kind == "place":
                    ep["notes"].append("no substation in OSM; using the centroid of the town it is named after")
                return

    def _validate(self, ep, utility, zone):
        if ep["pt"] is None:
            ep["confidence"] = "unlocated"
            ep["notes"].append("no OSM substation or Nominatim place matched")
            return
        c = ep["checks"]
        if utility == "GPC" and zone in self.zone_centroids and not c.get("organizer"):
            d = haversine_km(ep["pt"], self.zone_centroids[zone])
            c["zone_km"] = round(d, 1)
            limit = self.zone_radius[zone]
            c["zone_ok"] = d <= limit
            if not c["zone_ok"]:
                ep["notes"].append(
                    f"REJECTED {ep['source']}: {d:.0f} km from the zone {zone} centroid "
                    f"(zone radius {limit:.0f} km) -- same name, wrong part of the state"
                )
                ep["rejected_source"], ep["rejected_pt"] = ep["source"], ep["pt"]
                ep.update(pt=None, source=None, confidence="rejected")
                return
        if c.get("organizer"):
            ep["confidence"] = "confirmed"
        elif (c.get("name_score", 0) >= STRONG and c.get("operator_ok")
              and not c.get("town_centroid") and c.get("ambiguous_resolved", True)
              and c.get("zone_ok", True)):
            ep["confidence"] = "confirmed"
        elif (c.get("name_score") == 100 and not c.get("operator_tagged", True) and c.get("unique_site")
              and c.get("zone_ok", True)):
            # OSM often leaves operator blank; an exact, unique name in the right state is still solid
            ep["confidence"] = "confirmed"
            ep["notes"].append("confirmed: exact name, only such substation in the state; OSM has no operator tag")
        else:
            ep["confidence"] = "low_confidence"
            why = []
            if c.get("town_centroid"):
                why.append("town centroid, not the substation itself")
            if c.get("name_score", 100) < STRONG:
                why.append(f"fuzzy name match ({c['name_score']})")
            if "operator_ok" in c and not c["operator_ok"]:
                why.append("OSM operator tag missing or not this utility")
            if c.get("ambiguous_resolved") is False:
                why.append("ambiguous, several same-named substations")
            ep["notes"].append("low confidence: " + "; ".join(why))

    def build_zone_centroids(self, gpc_projects):
        """Median of strongly-matched GPC stations per planning zone."""
        anchors = {}
        for p in gpc_projects:
            for s in p["stations"]:
                norm = normalize(s)
                if not norm or NOT_A_PLACE.match(norm):
                    continue
                cands = [c for c in self.osm_candidates(norm, "GPC") if c["score"] >= STRONG and c["operator_ok"]]
                sites = {(round(c["pt"][0], 2), round(c["pt"][1], 2)) for c in cands}
                if len(sites) == 1:  # unambiguous only
                    anchors.setdefault(p["zone"], []).append(cands[0]["pt"])
        self.zone_centroids = {
            z: (statistics.median(p[0] for p in pts), statistics.median(p[1] for p in pts))
            for z, pts in anchors.items() if len(pts) >= 2
        }
        # radius = 1.25x the farthest anchor, so big rural zones aren't penalized
        self.zone_radius = {
            z: min(ZONE_KM_MAX, max(ZONE_KM, 1.25 * max(haversine_km(p, c) for p in anchors[z])))
            for z, c in self.zone_centroids.items()
        }
        return {z: len(v) for z, v in anchors.items()}


def geocode_project(stations, utility, geocoder, zone=None):
    """Locate every endpoint, then compute the center point and project confidence."""
    eps = []
    for s in stations:
        anchor = next((e["pt"] for e in eps if e["pt"] and e["confidence"] == "confirmed"), None)
        eps.append(geocoder.locate(s, utility, zone=zone, anchor=anchor))

    located = [e for e in eps if e["pt"]]
    notes = []
    if len(located) >= 2:
        span = max(haversine_km(a["pt"], b["pt"]) for a in located for b in located)
        if span > LINE_SPAN_KM:
            notes.append(f"endpoints are {span:.0f} km apart (> {LINE_SPAN_KM} km); at least one match is suspect")
            for e in located:
                if e["confidence"] == "confirmed" and not e["checks"].get("organizer"):
                    e["confidence"] = "low_confidence"
    if not located:
        return {"endpoints": eps, "center": None, "confidence": "unlocated", "notes": notes}

    places = [e for e in eps if e["confidence"] != "not_a_place"]
    center = (sum(e["pt"][0] for e in located) / len(located), sum(e["pt"][1] for e in located) / len(located))
    conf = "confirmed" if all(e["confidence"] == "confirmed" for e in located) else "low_confidence"
    if len(located) < len(places):
        notes.append(f"{len(located)} of {len(places)} endpoints located; center uses the located one(s) only")
    return {"endpoints": eps, "center": center, "confidence": conf, "notes": notes}
