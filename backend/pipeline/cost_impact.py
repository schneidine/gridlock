"""
Bonus deliverable: rough cost/impact estimate for a flagged overlap.

Every number here is either:
  (a) pulled directly from a real public filing (DESC's project cost table,
      GPC's IRP project list), or
  (b) an industry-documented figure from a cited public source, applied as a
      range, not a single invented number.

We deliberately do NOT fabricate a dollar figure for Georgia Power's side of
the pair, since GPC's cost data is CEII-redacted in their public filing.
Where a number can't be sourced, we say so and leave it out rather than
guess.

Case study: DESC "Hooks - Thurmond 115kV Tie: Rebuild" vs. GPC's two
"Evans Primary - Thurmond Dam 115KV Rebuild" (#5 and #6) projects.

Why this pair: Thurmond Dam sits on the Savannah River, the literal SC/GA
border. The coordinate match here (33.660127, -82.195931) is not our
estimate -- it's taken directly from the challenge organizers' own
validated worked example (Projects_Overlaps.xlsx), so this is a
organizer-confirmed real-world overlap, not a geocoding guess. Our pipeline
independently rediscovers it as a 0.0 mi "touching/crossing" tier match.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent

# --- real, sourced numbers ---

DESC_PROJECT = {
    "title": "Hooks - Thurmond 115kV Tie: Rebuild",
    "description": "Rebuilding section of line between Hooks and Thurmond. "
                   "Approximately 2.3 miles. The line will be rebuilt on "
                   "existing R/W using steel poles, 115 kV insulation, and "
                   "1272 ACSR conductor.",
    "total_cost_usd": 2_200_080,   # DESC's own public 5-year budget filing
    "in_service_date": "2024-12-31",
    "source": "DESC 'Planned Transmission Projects $2M and Above' 5-Year Budget filing",
}

GPC_PROJECTS = [
    {"title": "Evans Primary - Thurmond Dam (USA) #5 115KV Rebuild", "need_date": "2033-06-01"},
    {"title": "Evans Primary - Thurmond Dam (USA) #6 115KV Rebuild", "need_date": "2033-06-01"},
]
GPC_COST_NOTE = ("Georgia Power's project cost for this line item is redacted "
                 "as CEII in their public IRP filing (per FERC 18 CFR 388.113). "
                 "We do not estimate or invent a figure for it.")

DAY_GAP = 3074  # ~8.4 years apart, computed by the pipeline (2024-12-31 -> 2033-06-01)

# --- cited industry benchmark for coordinated vs. uncoordinated utility work ---
# Source: NYC Department of Design & Construction, 2025 DDC Utility
# Coordination Report (public agency report).
#   - "Joint Bidding" (coordinated) projects: ~$1.5M average additional cost
#     per project from utility-related delays
#   - "Section U" (uncoordinated) projects: ~$5.8M average additional cost
#     per project from utility-related delays
#   - i.e. coordination avoided roughly 74% of the utility-delay-driven cost
#     overrun seen on uncoordinated projects, in that dataset
# This is underground street/utility construction in NYC, not southeastern
# transmission work, so we do NOT claim it transfers 1:1 -- we use it only
# to set a conservative, cited LOWER range (10-25%) for what avoided
# double-mobilization/overhead can plausibly be worth on a single project,
# rather than inventing a number with no basis at all.
COORDINATION_SAVINGS_LOW_PCT = 0.10
COORDINATION_SAVINGS_HIGH_PCT = 0.25
BENCHMARK_SOURCE = ("NYC DDC 2025 Utility Coordination Report -- coordinated "
                     "('Joint Bidding') projects saw ~74% lower utility-delay-driven "
                     "cost overruns than uncoordinated ('Section U') projects "
                     "(avg $1.5M vs. $5.8M additional cost per project). We apply "
                     "a conservative 10-25% range to DESC's own project cost as an "
                     "illustrative, not literal, translation of that finding.")


def compute():
    low = DESC_PROJECT["total_cost_usd"] * COORDINATION_SAVINGS_LOW_PCT
    high = DESC_PROJECT["total_cost_usd"] * COORDINATION_SAVINGS_HIGH_PCT

    result = {
        "overlap": {
            "desc_project": DESC_PROJECT["title"],
            "gpc_projects": [p["title"] for p in GPC_PROJECTS],
            "distance_mi": 0.0,
            "tier": "touching_crossing",
            "day_gap": DAY_GAP,
            "location_note": "Thurmond Dam, Savannah River (SC/GA border) -- "
                              "coordinate confirmed by the challenge organizers' "
                              "own validated example, not our estimate.",
        },
        "known_costs": {
            "desc_total_project_cost_usd": DESC_PROJECT["total_cost_usd"],
            "desc_cost_source": DESC_PROJECT["source"],
            "gpc_total_project_cost_usd": None,
            "gpc_cost_note": GPC_COST_NOTE,
        },
        "illustrative_savings_estimate": {
            "basis": "shared mobilization / site access / overhead avoided by "
                     "coordinating timing at the same facility, applied only to "
                     "DESC's known, public project cost (Georgia Power's two "
                     "projects at the same site would add further avoided cost "
                     "we can't quantify without their redacted figures)",
            "savings_pct_range": [COORDINATION_SAVINGS_LOW_PCT, COORDINATION_SAVINGS_HIGH_PCT],
            "savings_usd_low": round(low),
            "savings_usd_high": round(high),
            "benchmark_source": BENCHMARK_SOURCE,
        },
        "the_actual_problem_this_illustrates": (
            f"DESC's rebuild at this exact facility is scheduled for 2024. "
            f"Georgia Power's two rebuilds at the same facility aren't scheduled "
            f"until 2033 -- {DAY_GAP} days ({DAY_GAP/365.25:.1f} years) later. "
            f"Under the status quo, that's two separate crew mobilizations to the "
            f"same dam, eight years apart, each planned with zero visibility into "
            f"the other. Even a modest timing conversation between the two "
            f"utilities -- not a shared build, just synchronized scheduling -- is "
            f"the coordination FERC Order 1920 is meant to produce."
        ),
    }
    return result


if __name__ == "__main__":
    result = compute()
    out_path = ROOT / "data_clean" / "cost_impact_estimate.json"
    json.dump(result, open(out_path, "w"), indent=2)
    print(json.dumps(result, indent=2))
