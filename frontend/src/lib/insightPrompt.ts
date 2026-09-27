import type { CostImpact, Overlap, Project } from "./types";
import { TIER_LABEL } from "./types";

// What each tier lets the two utilities do, per the challenge brief.
const TIER_MEANING: Record<Overlap["tier"], string> = {
  touching_crossing: "the projects touch or cross, so the utilities must coordinate outage timing and crossing structures",
  share_land: "under 1.6 km apart, close enough to share the land itself: right-of-way, access roads, permits",
  share_logistics: "under 8 km apart, close enough to share site logistics: laydown yards and material deliveries",
  share_crews: "under 40 km apart, within a crew's morning drive, so they could share crews, cranes and contractors",
};

const CONF_MEANING: Record<string, string> = {
  confirmed: "confirmed on a map",
  estimated: "estimated (not verified)",
  region_only: "only known to the region level, so distances are rough",
};

function describeProject(label: string, p: Project) {
  return [
    `${label} project: ${p.title}`,
    `  Utility: ${p.utility} (${p.state})`,
    p.description && `  Description: ${p.description}`,
    p.status && `  Status: ${p.status}`,
    p.in_service_date && `  In-service date: ${p.in_service_date}`,
    p.stations.length > 0 && `  Stations: ${p.stations.join(", ")}`,
    `  Location: ${CONF_MEANING[p.geo_confidence ?? "region_only"]}`,
  ]
    .filter(Boolean)
    .join("\n");
}

export function buildPrompt(o: Overlap, a: Project, b: Project, ci: CostImpact | undefined) {
  const facts = [
    describeProject("Dominion Energy South Carolina (DESC)", a),
    describeProject("Georgia Power (GPC)", b),
    `Closest distance between the projects: ${o.distance_mi} miles`,
    `Overlap tier: ${TIER_LABEL[o.tier]} (${TIER_MEANING[o.tier]})`,
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

  return `You advise transmission planners at DESC and Georgia Power. Geographic closeness is the main reason to coordinate; similar build dates (within about a year) make it much stronger; build dates years apart make it weak unless one schedule could move.

A flagged pair of planned projects:

${facts}

Tell the planner what this match actually means for them. Be direct and specific to these two projects; do not restate the facts back or explain what a utility is.

Reply in plain text (no markdown, no asterisks, no bullets) using exactly these five labelled lines, each 1-2 sentences:
Verdict: High, Medium or Low priority, and the single main reason.
What they are: what each project physically builds, in plain words.
What they could share: the concrete thing the tier allows for these two projects specifically.
Timing: whether the schedules line up and what that means for coordinating.
Check first: the biggest uncertainty to confirm before acting (for example location confidence, redacted costs, or schedule slip).

Only use the facts above. If something is unknown, say so instead of guessing.`;
}
