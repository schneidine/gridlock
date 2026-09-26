export type Tier = "touching_crossing" | "share_land" | "share_logistics" | "share_crews";
export type Confidence = "confirmed" | "estimated" | "region_only";

export interface Project {
  project_id: string;
  utility: string;
  state: string;
  title: string;
  description: string | null;
  status: string | null;
  in_service_date: string | null;
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
  touching_crossing: "Touching / Crossing",
  share_land: "Share Right-of-Way",
  share_logistics: "Share Logistics",
  share_crews: "Share Crews",
};

export const TIER_COLOR: Record<Tier, string> = {
  touching_crossing: "#dc2626",
  share_land: "#f59e0b",
  share_logistics: "#eab308",
  share_crews: "#84cc16",
};
