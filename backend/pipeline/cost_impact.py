"""
Bonus deliverable: rough cost/impact estimate for the top-ranked overlap.

Reads the ranked overlap table (data_clean/sentinel_dataset.json), takes the
highest-scoring confirmed pair whose DESC side has a public cost, and frames
the saving as "one mobilization instead of two".

Every number is either:
  (a) pulled from a public filing (DESC's cost table and description), or
  (b) a stated assumption, applied as a range and labelled as such.

Georgia Power's costs are CEII-redacted in their public IRP, so we never
estimate a GPC dollar figure; DESC's cost is used as a proxy for scale.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATASET = ROOT / "data_clean" / "sentinel_dataset.json"
OUT = ROOT / "data_clean" / "cost_impact_estimate.json"

# Assumption: mobilization/demobilization (crew travel, equipment haul, staging
# yard, site setup, traffic/ROW access, safety stand-up) is typically a few
# percent of a transmission construction contract. Many state DOT specs cap the
# mobilization pay item at ~10%; we use a conservative 3-5%.
MOBILIZATION_PCT = (0.03, 0.05)
SAME_SEASON_DAYS = 365  # within a year, work can realistically be sequenced together

BENCHMARK_SOURCE = (
    "Context: NYC DDC 2025 Utility Coordination Report found coordinated ('Joint Bidding') "
    "projects averaged ~$1.5M in utility-delay cost vs ~$5.8M for uncoordinated ones (~74% less). "
    "That is urban underground work, so we do not apply it directly; it only suggests our "
    "3-5% mobilization-only figure is a floor, not a ceiling."
)
GPC_COST_NOTE = (
    "Georgia Power's cost for this project is redacted as CEII in the public IRP filing. "
    "We do not estimate it; DESC's public cost is used only as a proxy for job scale."
)


def line_miles(description):
    m = re.search(r"(\d+(?:\.\d+)?)\s*miles?", description or "")
    return float(m.group(1)) if m else None


def compute():
    data = json.load(open(DATASET))
    projects = {p["project_id"]: p for p in data["desc_projects"] + data["gpc_projects"]}
    # the estimate below is written for a DESC x Georgia Power pair (GPC costs are CEII-redacted)
    top = next(o for o in data["overlaps"]
               if o["confidence"] == "confirmed" and o["utility_b"] == "Georgia Power"
               and projects[o["project_id_a"]].get("total_cost_usd"))
    desc, gpc = projects[top["project_id_a"]], projects[top["project_id_b"]]
    cost = desc["total_cost_usd"]
    miles = line_miles(desc.get("description"))
    low, high = (round(cost * p) for p in MOBILIZATION_PCT)
    gap = top["day_gap"]
    narrative = (
        f"{desc['title']} (DESC, ${cost:,}"
        + (f", {miles:g} mi of new 230 kV line, ~${cost / miles / 1e6:.1f}M/mi" if miles else "")
        + f") and {gpc['title']} (Georgia Power) are {top['distance_mi']} mi apart and due "
        f"{gap} days apart. Both touch the same 230 kV corridor across the Savannah River near "
        f"Hardeeville/Purrysburg, so they can share a staging yard, crews, equipment haul and, "
        f"most importantly, one coordinated outage window, instead of each utility mobilizing "
        f"separately. Avoiding one mobilization is worth roughly ${low / 1e6:.1f}M-${high / 1e6:.1f}M "
        f"before any shared right-of-way or outage-planning savings."
    )

    return {
        "overlap": {
            "rank": top["rank"],
            "score": top["score"],
            "desc_project": desc["title"],
            "desc_project_id": desc["project_id"],
            "gpc_project": gpc["title"],
            "gpc_projects": [gpc["title"]],  # list form the frontend seed script reads
            "gpc_project_id": gpc["project_id"],
            "distance_mi": top["distance_mi"],
            "day_gap": gap,
            "desc_in_service": desc["in_service_date"],
            "gpc_need_date": gpc["in_service_date"],
            "tier": top["tier"],
            "location_note": "Savannah River 230 kV corridor near Hardeeville, SC / Purrysburg",
        },
        "known_costs": {
            "desc_total_project_cost_usd": cost,
            "desc_line_miles": miles,
            "desc_cost_per_mile_usd": round(cost / miles) if miles else None,
            "desc_cost_source": "DESC 'Planned Transmission Projects $2M and Above' 5-Year Budget filing",
            "gpc_total_project_cost_usd": None,
            "gpc_cost_note": GPC_COST_NOTE,
        },
        "illustrative_savings_estimate": {
            "framing": "one mobilization instead of two",
            "assumption": f"mobilization = {MOBILIZATION_PCT[0]:.0%}-{MOBILIZATION_PCT[1]:.0%} of contract cost, "
                          f"proxied by DESC's public ${cost:,} for this job",
            "savings_pct_range": list(MOBILIZATION_PCT),
            "savings_usd_low": low,
            "savings_usd_high": high,
            "timing_feasible": gap is not None and gap <= SAME_SEASON_DAYS,
            "benchmark_source": BENCHMARK_SOURCE,
        },
        "narrative": narrative,
        "the_actual_problem_this_illustrates": narrative,  # key the frontend seed script reads
    }


if __name__ == "__main__":
    result = compute()
    json.dump(result, open(OUT, "w"), indent=2)
    print(json.dumps(result, indent=2))
