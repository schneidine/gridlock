"""
Parse Dominion Energy South Carolina's public "$2M and Above" 5-Year Budget
PDF into a structured project list.

Input:  data_raw/utility-filings/DESC_5yr_transmission_projects.pdf
Output: data_clean/desc_projects_raw.json

Each PDF page is one project, laid out as a fixed set of labeled fields
(Project ID, Project Description, Project Need, Project Status, Planned
In-Service Date, Estimated Project Cost). We parse it structurally rather
than with a single regex, since fields vary in line count.
"""
import json
import re
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).parent.parent
PDF_PATH = ROOT / "data_raw" / "utility-filings" / "DESC_5yr_transmission_projects.pdf"
OUT_PATH = ROOT / "data_clean" / "desc_projects_raw.json"


def extract_stations(name: str):
    """Pull the named substations/stations out of a project title.

    Strategy: strip a leading zone prefix (e.g. "SAV:"), strip any
    dual-voltage class marker (e.g. "230-115kV"), then split on the
    remaining text up to the first single voltage marker (e.g. "115 kV"),
    using dashes as the separator between station names.
    """
    name2 = re.sub(r"[\x00-\x1f]", "", name)  # strip stray control chars from the PDF
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
    projects = []
    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split("\n")

            idx_pid = lines.index("Project ID")
            idx_desc = lines.index("Project Description")
            idx_need = lines.index("Project Need")
            idx_status = lines.index("Project Status")
            idx_date = lines.index("Planned In-Service Date")
            idx_cost = lines.index("Estimated Project Cost")

            title = " ".join(lines[4:idx_pid]).strip()
            pid = lines[idx_pid + 1].strip()
            desc = " ".join(lines[idx_desc + 1 : idx_need]).strip()
            need = " ".join(lines[idx_need + 1 : idx_status]).strip()
            status = lines[idx_status + 1].strip()
            date = lines[idx_date + 1].strip()

            # cost table: header row then a values row; Total is the last $ figure
            header = lines[idx_cost + 1].replace("*", "").split()
            values_line = lines[idx_cost + 2]
            dollar_amounts = re.findall(r"\$[\d,]+", values_line)
            total_cost_raw = dollar_amounts[-1] if dollar_amounts else None
            total_cost_usd = (
                int(total_cost_raw.replace("$", "").replace(",", "")) if total_cost_raw else None
            )
            yearly_raw = dict(zip(header[:-1], dollar_amounts[:-1]))
            yearly, flags = validate_costs(yearly_raw, total_cost_usd)

            projects.append(
                {
                    "project_id_raw": pid,
                    "title": title,
                    "description": desc,
                    "need": need,
                    "status": status,
                    "in_service_date": date,
                    "total_cost_raw": total_cost_raw,
                    "total_cost_usd": total_cost_usd,
                    "yearly_cost_raw": yearly_raw,
                    "yearly_cost_usd": yearly,
                    "stations": extract_stations(title),
                    "data_quality_flags": flags,
                }
            )

    # same endpoints, different scope (e.g. 6809 E vs 6809 G) -- keep both, but say so
    by_route = {}
    for p in projects:
        by_route.setdefault(tuple(p["stations"]), []).append(p["project_id_raw"])
    for p in projects:
        twins = [t for t in by_route[tuple(p["stations"])] if t != p["project_id_raw"]]
        if twins:
            p["data_quality_flags"].append(
                f"same named endpoints as project {', '.join(twins)} (different scope/ID) -- kept as separate rows"
            )
    return projects


WELL_FORMED = re.compile(r"^\$\d{1,3}(,\d{3})*$")


def validate_costs(yearly_raw, total):
    """Parse the yearly cost cells and cross-check them against the listed total.

    Catches malformed thousands grouping (e.g. "$19,00,181") and repairs it only
    when the total pins down the value exactly; otherwise it just flags.
    """
    flags = []
    yearly = {}
    bad = []
    for year, raw in yearly_raw.items():
        yearly[year] = int(raw.replace("$", "").replace(",", ""))
        if not WELL_FORMED.match(raw):
            bad.append(year)
    if total is None:
        return yearly, ["no total cost parsed"]
    if len(bad) == 1:
        year = bad[0]
        implied = total - sum(v for y, v in yearly.items() if y != year)
        flags.append(
            f"malformed cost cell {year}={yearly_raw[year]}; repaired to ${implied:,} "
            f"(the only value consistent with the listed total ${total:,})"
        )
        yearly[year] = implied
    elif bad:
        flags.append(f"malformed cost cells {bad}; not repaired")
    diff = total - sum(yearly.values())
    if diff:
        flags.append(
            f"yearly figures sum to ${sum(yearly.values()):,} but listed total is ${total:,} "
            f"(${diff:,} unaccounted for, likely spend beyond the 5-year window); listed total kept"
        )
    return yearly, flags


def main():
    projects = parse()
    OUT_PATH.parent.mkdir(exist_ok=True)
    json.dump(projects, open(OUT_PATH, "w"), indent=2)
    print(f"Parsed {len(projects)} DESC projects -> {OUT_PATH}")
    missing_cost = [p for p in projects if p["total_cost_usd"] is None]
    if missing_cost:
        print(f"WARNING: {len(missing_cost)} projects missing a parsed cost")
    for i, p in enumerate(projects, 1):
        for f in p["data_quality_flags"]:
            print(f"  DESC project {i} ({p['project_id_raw']}): {f}")


if __name__ == "__main__":
    main()
