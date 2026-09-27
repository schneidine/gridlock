"""
Registry of every source document the pipeline reads.

Each entry names the raw input file (under data_raw/) and the parsed project
list it should produce (under data_clean/). `parser` says what reads it:

  - "hand": a hand-validated pdfplumber/regex parser already in pipeline/
  - "ai":   not parsed yet -- to be read by the AI extraction step
  - "excluded": deliberately not parsed (see the entry's "reason")

To add a new source, drop the file under data_raw/ and add an entry here.
"""
from pathlib import Path

ROOT = Path(__file__).parent.parent
RAW = ROOT / "data_raw" / "utility-filings"
CLEAN = ROOT / "data_clean"

SOURCES = {
    "desc_5yr": {
        "publisher": "Dominion Energy South Carolina (SCRTP)",
        "title": "Planned Transmission Projects $2M and Above, 5-Year Budget",
        "input": RAW / "DESC_5yr_transmission_projects.pdf",
        "output": CLEAN / "desc_projects_raw.json",
        "parser": "hand",  # pipeline/parse_desc_pdf.py
    },
    "gpc_irp_2025": {
        "publisher": "Georgia Power",
        "title": "2025 IRP Technical Appendix Vol. 3, Table 2 (ITS 10-Year Expansion Plan)",
        "input": RAW / "GPC_2025_IRP_Volume3_transmission_plan.txt",
        "output": CLEAN / "gpc_projects_raw.json",
        "parser": "hand",  # pipeline/parse_gpc_irp.py
    },
    "sertp_2025_regional_plan": {
        "publisher": "SERTP",
        "title": "2025 Regional Transmission Plan and Input Assumptions",
        "url": "https://www.southeasternrtp.com/docs/general/2025/2025%20Regional%20Transmission%20Plan%20and%20Input%20Assumptions.pdf",
        "input": RAW / "sertp" / "SERTP_2025_Regional_Transmission_Plan.pdf",
        "output": CLEAN / "sertp_2025_regional_plan_projects_raw.json",
        "parser": "excluded",
        "reason": "project pages carry a '(CEII)' banner and the challenge rules put anything "
                  "marked CEII off-limits; the Non-CEII preliminary report covers the same projects",
    },
    "sertp_2025_preliminary_plan": {
        "publisher": "SERTP",
        "title": "2025 SERTP Preliminary Expansion Plan Report (Non-CEII)",
        "url": "https://www.southeasternrtp.com/docs/general/2025/2025%20SERTP%20Preliminary%20Expansion%20Plan%20Report%20(Non-CEII).pdf",
        "input": RAW / "sertp" / "SERTP_2025_Preliminary_Expansion_Plan_NonCEII.pdf",
        "output": CLEAN / "sertp_2025_preliminary_plan_projects_raw.json",
        "parser": "hand",  # pipeline/parse_sertp_pdf.py
    },
}


def ai_sources():
    """Sources waiting on the AI extraction step."""
    return {k: v for k, v in SOURCES.items() if v["parser"] == "ai"}


if __name__ == "__main__":
    for key, s in SOURCES.items():
        status = "ok" if s["input"].exists() else "MISSING"
        print(f"{key:30s} [{s['parser']:8s}] {status:7s} {s['input'].relative_to(ROOT)} -> {s['output'].relative_to(ROOT)}")
