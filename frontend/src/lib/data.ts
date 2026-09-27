import { createClient } from "@/lib/supabase/server";
import type { CostImpact, Overlap, PlannerNote, Project } from "@/lib/types";

export async function getProjects(): Promise<Project[]> {
  const supabase = await createClient();
  const { data, error } = await supabase.from("projects").select("*");
  if (error) throw error;
  return data as Project[];
}

export async function getOverlaps(): Promise<Overlap[]> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("overlaps")
    .select("*")
    .order("distance_km", { ascending: true });
  if (error) throw error;
  return data as Overlap[];
}

export async function getCostImpact(): Promise<CostImpact[]> {
  const supabase = await createClient();
  const { data, error } = await supabase.from("cost_impact").select("*");
  if (error) throw error;
  return data as CostImpact[];
}

export async function getPlannerNotes(): Promise<PlannerNote[]> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("planner_notes")
    .select("*")
    .order("created_at", { ascending: true });
  if (error) throw error;
  return data as PlannerNote[];
}
