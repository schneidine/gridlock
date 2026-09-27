"""
Pull the named substations/stations out of a project title. Shared by the
DESC, GPC and SERTP parsers so every source is handled the same way.

A title can name several routes or stations, e.g.
  "VCS1-Denny Terrace 230kV & VCS1-Pineland 230kV: Rebuild ..."
  "Okatie 230-115kV Substation, Jasper – Yemassee 230kV #1 Fold-in"
so we split it into clauses on " & ", "," and " and ". The first clause always
names the project's place; a later clause only counts if it is another route
("A - B") or another substation ("X Sub") and doesn't name equipment, so
scope clauses ("Replace Sw House", "Spare 230-115kV", "BUS-TIE BREAKER") are
skipped. Each clause is read up to its first voltage marker, using dashes
between station names. Parentheticals like "(SAV)" are kept for the geocoder.
"""
import re

CLAUSE_SPLIT = re.compile(r"\s+&\s+|,|\s+and\s+", re.IGNORECASE)  # "LG&E" has no spaces, stays whole
VOLTAGE = re.compile(r"\d+(\.\d+)?(\s*[/\-]\s*\d+(\.\d+)?)*\s*kv", re.IGNORECASE)  # 115 kV, 230-115kV, 230/100/44 KV
ROUTE_DASH = re.compile(r"[A-Za-z0-9]\s*[-–]\s*[A-Z]")  # "VCS1-Pineland" is a route, "Fold-in" is not
SCOPE_WORDS = re.compile(
    r"\b(bus|breakers?|jumpers?|bank|transformers?|relays?|switch|trap|loop|re|termination|reconductor|phase)\b",
    re.IGNORECASE,
)
SUB_LABEL = re.compile(r"\b(Sub|Substation)\b", re.IGNORECASE)


def another_place(clause):
    place = clause.split(":")[0]  # "AM Williams Sub: Replace Sw House" -> judge "AM Williams Sub"
    return bool(ROUTE_DASH.search(place) or SUB_LABEL.search(place)) and not SCOPE_WORDS.search(place)


def tidy(part):
    part = re.split(r"[:,]", part)[0].strip()
    part = re.sub(r"\b(Sub|Substation|Tap|Line|Transmission)\b\.?$", "", part, flags=re.IGNORECASE).strip()
    return re.sub(r"\s+", " ", part)


def clause_stations(clause):
    m = VOLTAGE.search(clause)
    route = (clause[: m.start()] if m else clause).strip(" -–:,")
    return [tidy(p) for p in re.split(r"\s*[-–]\s*", route) if p.strip()]


def extract_stations(name: str):
    name = re.sub(r"[\x00-\x1f]", "", name)
    name = re.sub(r"^[A-Z]{2,6}:\s*", "", name)  # zone/owner prefix, e.g. "SAV:", "GTC:"
    name = re.sub(r"(\d)O(?=\s*kv)", r"\g<1>0", name, flags=re.IGNORECASE)  # "23O KV" typo in the GPC table
    clauses = CLAUSE_SPLIT.split(name)
    stations = []
    for i, clause in enumerate(clauses):
        # "THALMANN AND COLERAIN 230 KV ...": a bare name joined to the clause carrying the voltage
        joined = i == 1 and not re.search(r"[:\d]", clauses[0]) and VOLTAGE.search(clause)
        if i > 0 and not (another_place(clause) or joined):
            continue
        for s in clause_stations(clause):
            if len(s) > 1 and re.search(r"[A-Za-z]", s) and s.lower() not in (x.lower() for x in stations):
                stations.append(s)
    return stations
