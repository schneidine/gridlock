"""
Parse Georgia Power's 2025 IRP Technical Appendix Volume 3, Table 2
("Georgia ITS 10-Year Expansion Plan Projects List") into a structured
project list.

Input:  data_raw/utility-filings/GPC_2025_IRP_Volume3_transmission_plan.txt
        (plain-text extraction of the public IRP PDF)
Output: data_clean/gpc_projects_raw.json

The table spans many pages with repeated headers/footers/CEII notices
interleaved, and project names sometimes wrap across 2-3 lines before the
row's need-date/sponsor column appears. We strip the boilerplate lines,
then reconstruct rows by matching a "zone year TEAMS-number ..." row-start
pattern and a "... date SPONSOR REDACTED..." row-end pattern, joining
everything in between as the project name.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
TXT_PATH = ROOT / "data_raw" / "utility-filings" / "GPC_2025_IRP_Volume3_transmission_plan.txt"
OUT_PATH = ROOT / "data_clean" / "gpc_projects_raw.json"

TABLE_HEADER = "Table 2 Georgia ITS 10 Year Plan Project List"

JUNK_PATTERNS = [
    r"^PUBLIC DISCLOSURE",
    r"^CRITICAL ENERGY INFRASTRUCTURE",
    r"^contents shall",
    r"^policy, should not",
    r"^\d{4} GA ITS Ten-Year Plan",
    r"^Zone Year TEAMS",
    r"^Number Project Name Need Date",
    r"^Project\s*$",
    r"^Sponsor Estimated Cost",
    r"^Estimated Cost -",
    r"^DU Totals",
    r"^\s*$",
]

ROW_START_RE = re.compile(r"^(\d{3})\s+(\d{4})\s+(\d+)\s+(.*)$")
ROW_END_RE = re.compile(r"^(.*?)\s*(\d{1,2}/\d{1,2}/\d{4})\s+([A-Z]+)\s+REDACTED.*$")


def extract_stations(name: str):
    """Same station-extraction heuristic as the DESC parser (see
    parse_desc_pdf.py) so both utilities' project titles are handled
    consistently."""
    name2 = re.sub(r"[\x00-\x1f]", "", name)
    name2 = re.sub(r"^[A-Z]{2,6}:\s*", "", name2)
    name2 = re.sub(r"\d+(\.\d+)?\s*[/\-]\s*\d+(\.\d+)?\s*kv", " ", name2, flags=re.IGNORECASE)
    m = re.search(r"\d+(\.\d+)?\s?kv", name2, flags=re.IGNORECASE)
    route = name2[: m.start()] if m else name2
    route = route.strip(" -–:,")
    parts = re.split(r"\s*[-–]\s*", route)
    parts = [re.sub(r"\s+", " ", p).strip() for p in parts if p.strip()]

    def tidy(p):
        p = re.split(r"[:,&]", p)[0].strip()
        p = re.sub(r"\b(Sub|Substation|Tap|Line|Transmission)\b\.?$", "", p, flags=re.IGNORECASE).strip()
        return p

    parts = [tidy(p) for p in parts]
    return [p for p in parts if len(p) > 1]


def parse():
    all_lines = open(TXT_PATH).readlines()

    start_idx = end_idx = None
    for i, l in enumerate(all_lines):
        if l.strip() == TABLE_HEADER and i > 3800 and start_idx is None:
            start_idx = i + 1
        if l.strip().startswith("Total") and "REDACTED" in l and start_idx and end_idx is None:
            end_idx = i
            break
    if start_idx is None or end_idx is None:
        raise RuntimeError("Could not locate Table 2 boundaries -- has the IRP text format changed?")

    block = all_lines[start_idx:end_idx]
    clean_lines = [
        l.rstrip("\n")
        for l in block
        if not any(re.match(p, l.rstrip("\n")) for p in JUNK_PATTERNS)
    ]

    rows = []
    cur = None
    for l in clean_lines:
        m_start = ROW_START_RE.match(l)
        if m_start:
            if cur:
                rows.append(cur)
            zone, year, teams, rest = m_start.groups()
            cur = {"zone": zone, "year_col": year, "teams_number": teams, "name_parts": [rest] if rest else []}
            m_end_same = ROW_END_RE.match(rest)
            if m_end_same:
                namepart, date, sponsor = m_end_same.groups()
                cur["name_parts"] = [namepart]
                cur["need_date"] = date
                cur["sponsor"] = sponsor
                rows.append(cur)
                cur = None
            continue
        if cur is not None:
            m_end = ROW_END_RE.match(l)
            if m_end:
                namepart, date, sponsor = m_end.groups()
                if namepart.strip():
                    cur["name_parts"].append(namepart.strip())
                cur["need_date"] = date
                cur["sponsor"] = sponsor
                rows.append(cur)
                cur = None
            else:
                cur["name_parts"].append(l.strip())
    if cur:
        rows.append(cur)

    projects = []
    for r in rows:
        name = re.sub(r"\s+", " ", " ".join(p for p in r["name_parts"] if p)).strip()
        projects.append(
            {
                "zone": r["zone"],
                "year_col": r["year_col"],
                "teams_number": r["teams_number"],
                "project_name": name,
                "need_date": r.get("need_date"),
                "sponsor": r.get("sponsor"),
                "stations": extract_stations(name),
            }
        )
    return projects


def main():
    projects = parse()
    OUT_PATH.parent.mkdir(exist_ok=True)
    json.dump(projects, open(OUT_PATH, "w"), indent=2)
    print(f"Parsed {len(projects)} GPC/ITS rows -> {OUT_PATH}")
    from collections import Counter

    print("By sponsor:", Counter(p["sponsor"] for p in projects))


if __name__ == "__main__":
    main()
