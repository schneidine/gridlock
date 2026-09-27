import type { Confidence, CostImpact, Overlap, Project } from "./types";
import { TIER_LABEL } from "./types";

// What each category lets the two utilities do (rules in backend/pipeline/build_dataset.py).
const TIER_MEANING: Record<Overlap["tier"], string> = {
  shared_substation:
    "both projects work at the same substation, so the utilities must coordinate outages and the work at that station",
  same_window:
    "within 25 miles and in-service dates within 2 years, so they could share crews, equipment, staging yards and deliveries",
  schedules_apart:
    "within 25 miles but in-service dates more than 2 years apart (or unknown), so crews will not overlap; coordination is mostly sharing plans",
};

const CONF_MEANING: Record<Confidence, string> = {
  confirmed: "confirmed on a map",
  low_confidence: "estimated (not fully verified), so the distance is approximate",
};

function describeProject(label: string, p: Project) {
  return [
    `${label} project: ${p.title}`,
    `  Utility: ${p.utility} (${p.state})`,
    p.description && `  Description: ${p.description}`,
    p.status && `  Status: ${p.status}`,
    p.in_service_date && `  In-service date: ${p.in_service_date}`,
    p.stations.length > 0 && `  Stations: ${p.stations.join(", ")}`,
    `  Location: ${p.geo_confidence ? CONF_MEANING[p.geo_confidence] : "not located"}`,
  ]
    .filter(Boolean)
    .join("\n");
}

export function buildPrompt(o: Overlap, a: Project, b: Project, ci: CostImpact | undefined) {
  const facts = [
    describeProject("Dominion Energy South Carolina (DESC)", a),
    describeProject("Georgia Power (GPC)", b),
    `Distance between the two projects' center points: ${o.distance_mi} miles`,
    `Coordination category: ${TIER_LABEL[o.tier]} (${TIER_MEANING[o.tier]})`,
    o.day_gap != null
      ? `Gap between in-service dates: ${o.day_gap} days (about ${(o.day_gap / 365.25).toFixed(1)} years)`
      : "Gap between in-service dates: unknown",
    ci?.narrative && `Cost analysis notes: ${ci.narrative}`,
    ci?.savings_usd_low != null &&
      ci?.savings_usd_high != null &&
      `Estimated avoidable cost: $${Math.round(ci.savings_usd_low).toLocaleString("en-US")} to $${Math.round(ci.savings_usd_high).toLocaleString("en-US")}`,
  ]
    .filter(Boolean)
    .join("\n");

  return `You advise transmission planners at DESC and Georgia Power. Geographic closeness is the main reason to coordinate; similar build dates (within about two years) make it much stronger; build dates years apart make it weak unless one schedule could move.

A flagged pair of planned projects:

${facts}

Tell the planner what this match actually means for them. Be direct and specific to these two projects; do not restate the facts back or explain what a utility is.

Reply in plain text (no markdown, no asterisks, no bullets) using exactly these five labelled lines, each 1-2 sentences:
Verdict: High, Medium or Low priority, and the single main reason.
What they are: what each project physically builds, in plain words.
What they could share: the concrete thing the category allows for these two projects specifically.
Timing: whether the schedules line up and what that means for coordinating.
Check first: the biggest uncertainty to confirm before acting (for example location confidence, redacted costs, or schedule slip).

Only use the facts above. If something is unknown, say so instead of guessing.`;
}
