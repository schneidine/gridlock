// What a flagged pair could share; set by backend/pipeline/build_dataset.py (opportunity()).
export type Tier = "shared_substation" | "same_window" | "schedules_apart";
// Location confidence written by the pipeline's geocoder.
export type Confidence = "confirmed" | "low_confidence";

export interface Project {
  project_id: string;
  utility: string;
  state: string;
  title: string;
  description: string | null;
  status: string | null;
  in_service_date: string | null;
  in_service_year: number | null; // set alone when the source gives only a year (SERTP/Duke)
  stations: string[];
  geo_points: [number, number][] | null;
  geo_center: [number, number] | null;
  geo_confidence: Confidence | null;
  geo_notes: string[] | null;
}

export interface Overlap {
  id: number;
  project_id_a: string;
  project_id_b: string;
  distance_km: number;
  distance_mi: number;
  tier: Tier;
  day_gap: number | null;
  confidence: Confidence;
}

export interface CostImpact {
  id: number;
  overlap_id: number | null;
  desc_project_title: string;
  gpc_project_titles: string[];
  distance_mi: number;
  tier: Tier;
  day_gap: number | null;
  location_note: string | null;
  desc_total_cost_usd: number | null;
  desc_cost_source: string | null;
  gpc_total_cost_usd: number | null;
  gpc_cost_note: string | null;
  savings_pct_low: number | null;
  savings_pct_high: number | null;
  savings_usd_low: number | null;
  savings_usd_high: number | null;
  benchmark_source: string | null;
  narrative: string | null;
}

export interface PlannerNote {
  id: number;
  overlap_id: number;
  user_id: string;
  author_label: string;
  body: string;
  created_at: string;
}

export const TIER_LABEL: Record<Tier, string> = {
  shared_substation: "Shared Substation",
  same_window: "Same Build Window",
  schedules_apart: "Conflicting Schedules",
};

export const TIER_COLOR: Record<Tier, string> = {
  shared_substation: "#ef4444",
  same_window: "#f59e0b",
  schedules_apart: "#84cc16",
};

// Same ranking score as backend/pipeline/build_dataset.py score(): distance is the
// primary signal (70%), the in-service day gap the secondary one (30%), per the brief.
const THRESHOLD_MI = 25;
const MAX_GAP_DAYS = 1825;

export function overlapScore(o: Pick<Overlap, "distance_mi" | "day_gap">): number {
  const gap = Math.min(o.day_gap ?? MAX_GAP_DAYS, MAX_GAP_DAYS);
  return 0.7 * (1 - o.distance_mi / THRESHOLD_MI) + 0.3 * (1 - gap / MAX_GAP_DAYS);
}
