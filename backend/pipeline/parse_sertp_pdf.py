"""
Parse the SERTP (Southeastern Regional Transmission Planning) project
listings into a structured project list.

Input:  the "parser": "hand" SERTP entries in sources.py
Output: each entry's data_clean/sertp_*_projects_raw.json

Every project is a fixed block of labeled fields:

    In-Service Year: 2027
    Project Name:    GTC: JACKSON 115 KV, BUS AND JUMPER UPGRADES
    Description:     ...
    Supporting Statement(s): ...

The labels wrap unpredictably ("In-Service" / "2027" / "Year:", or
"Supporting <text>" / "Statement: <more text>"), so we cut the page text
into blocks at each "In-Service" line and then split each block on the
label lines, the same structural approach as parse_desc_pdf.py.

The Balancing Authority heading ("SOUTHERN Balancing Authority Area") is
read from the page's 18pt heading characters only: in the Regional Plan
it is overprinted on the page banner, so plain text extraction garbles it.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).parent))
from sources import ROOT, SOURCES
from stations import extract_stations

BLOCK_START = re.compile(r"^In-\s?Service\b")
PAGE_FOOTER = re.compile(r"^(Page \d+ of \d+|\d{1,3})$")
OWNER_PREFIX = re.compile(r"^([A-Z&]{2,6}):\s*")  # e.g. "GTC:", "MEAG:", "SAV:"


def balancing_authority(page):
    big = page.filter(lambda o: o.get("object_type") != "char" or o.get("size", 0) >= 16)
    head = (big.extract_text() or "").split("\n")[0]
    return re.sub(r"\s*(Balancing|Planning) Authority( Area)?\s*$", "", head).strip() or None


def parse_block(lines):
    """One project's lines, starting at its "In-Service" line -> dict."""
    i_name = next(i for i, l in enumerate(lines) if l.startswith("Project Name:"))
    i_desc = next(i for i, l in enumerate(lines) if l.startswith("Description:"))
    i_supp = next((i for i, l in enumerate(lines) if l.startswith("Supporting")), len(lines))

    years = re.findall(r"\b(20\d{2})\b", " ".join(lines[:i_name]))
    name = " ".join(lines[i_name:i_desc])[len("Project Name:"):]
    desc = " ".join(lines[i_desc:i_supp])[len("Description:"):]
    supp = lines[i_supp:]
    if supp:
        supp[0] = supp[0][len("Supporting"):]
        if len(supp) > 1:
            supp[1] = re.sub(r"^Statements?:", "", supp[1])
    clean = lambda s: re.sub(r"\s+", " ", s).strip()
    return {
        "in_service_year": int(years[0]) if years else None,
        "project_name": clean(name),
        "description": clean(desc),
        "supporting_statement": clean(" ".join(supp)),
    }


def parse(pdf_path):
    projects = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_no, page in enumerate(pdf.pages, 1):
            lines = [l.strip() for l in (page.extract_text() or "").split("\n")]
            starts = [i for i, l in enumerate(lines) if BLOCK_START.match(l)]
            if not starts or not any(l.startswith("Project Name:") for l in lines):
                continue  # not a project-listing page
            ba = balancing_authority(page)
            lines = [l for l in lines if not PAGE_FOOTER.match(l)]
            starts = [i for i, l in enumerate(lines) if BLOCK_START.match(l)]
            for a, b in zip(starts, starts[1:] + [len(lines)]):
                p = parse_block(lines[a:b])
                m = OWNER_PREFIX.match(p["project_name"])
                projects.append({
                    "balancing_authority": ba,
                    "owner_prefix": m.group(1) if m else None,
                    **p,
                    "page": page_no,
                    "stations": extract_stations(p["project_name"]),
                    "data_quality_flags": [],
                })
    return projects


def validate(projects, pdf_path):
    """Cross-check the parse against simple counts over the raw text."""
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    expected = len(re.findall(r"^Project Name:", text, re.M))
    if expected != len(projects):
        raise RuntimeError(f"parsed {len(projects)} projects but the PDF has {expected} 'Project Name:' labels")
    for p in projects:
        if p["in_service_year"] is None:
            p["data_quality_flags"].append("no in-service year found")
        if not p["description"]:
            p["data_quality_flags"].append("empty description")
        if not p["supporting_statement"]:
            p["data_quality_flags"].append("empty supporting statement")
        if p["balancing_authority"] is None:
            p["data_quality_flags"].append("no balancing authority heading on page")
    seen = Counter((p["project_name"], p["in_service_year"]) for p in projects)
    for p in projects:
        if seen[(p["project_name"], p["in_service_year"])] > 1:
            p["data_quality_flags"].append("same name and in-service year listed more than once -- kept as separate rows")


def main():
    for key, src in SOURCES.items():
        if not key.startswith("sertp") or src["parser"] != "hand":
            continue
        projects = parse(src["input"])
        validate(projects, src["input"])
        src["output"].parent.mkdir(exist_ok=True)
        json.dump(projects, open(src["output"], "w"), indent=2)
        print(f"Parsed {len(projects)} SERTP projects ({key}) -> {src['output'].relative_to(ROOT)}")
        print("  By balancing authority:", dict(Counter(p["balancing_authority"] for p in projects)))
        for p in projects:
            for f in p["data_quality_flags"]:
                print(f"  p.{p['page']} {p['project_name'][:60]}: {f}")


if __name__ == "__main__":
    main()
