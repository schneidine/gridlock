// Display metadata for each utility, keyed by the utility name the pipeline
// writes (backend/pipeline/build_dataset.py). Colors are literal hex because
// Leaflet draws them as SVG presentation attributes (see SentinelMap.tsx).
export const UTILITIES: Record<string, { short: string; state: string; color: string }> = {
  "Dominion Energy South Carolina": { short: "DESC", state: "SC", color: "#3b82f6" },
  "Georgia Power": { short: "GPC", state: "GA", color: "#f2762e" },
  "Duke Energy": { short: "DUKE", state: "NC/SC", color: "#a78bfa" },
};

export function utilityStyle(name: string) {
  return UTILITIES[name] ?? { short: name, state: "", color: "#94a3b8" };
}
