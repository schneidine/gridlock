#!/usr/bin/env node
/**
 * Loads the Python pipeline's output (../../backend/data_clean/*.json) into
 * Supabase. Uses the service-role key, which bypasses RLS, so this must
 * only ever be run from a trusted machine/CI -- never expose the
 * service-role key to the browser.
 *
 * Usage:
 *   SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... node scripts/seed.mjs
 *
 * Re-running this script replaces the contents of projects/overlaps/
 * cost_impact (planner_notes, being user-generated, is left untouched).
 */
import { createClient } from "@supabase/supabase-js";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, "..", "..", "backend", "data_clean");

const SUPABASE_URL = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
const SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!SUPABASE_URL || !SERVICE_ROLE_KEY) {
  console.error(
    "Missing SUPABASE_URL (or NEXT_PUBLIC_SUPABASE_URL) or SUPABASE_SERVICE_ROLE_KEY env vars."
  );
  process.exit(1);
}

const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
  auth: { persistSession: false },
});

function readJson(name) {
  return JSON.parse(readFileSync(path.join(DATA_DIR, name), "utf8"));
}

function projectRow(p) {
  return {
    project_id: p.project_id,
    utility: p.utility,
    state: p.state,
    title: p.title,
    description: p.description ?? null,
    status: p.status ?? null,
    in_service_date: p.in_service_date ? p.in_service_date.slice(0, 10) : null,
    stations: p.stations ?? [],
    geo_points: p.geo ? p.geo.points : null,
    geo_center: p.geo ? p.geo.center : null,
    geo_confidence: p.geo ? p.geo.confidence : null,
    geo_notes: p.geo ? p.geo.geocode_notes : null,
  };
}

async function main() {
  const dataset = readJson("sentinel_dataset.json");
  const costImpact = readJson("cost_impact_estimate.json");

  const allProjects = [...dataset.desc_projects, ...dataset.gpc_projects].map(projectRow);
  console.log(`Upserting ${allProjects.length} projects...`);
  {
    const { error } = await supabase.from("projects").upsert(allProjects, { onConflict: "project_id" });
    if (error) throw error;
  }

  console.log(`Replacing overlaps table (${dataset.overlaps.length} rows)...`);
  {
    const { error: delErr } = await supabase.from("overlaps").delete().neq("id", -1);
    if (delErr) throw delErr;

    const overlapRows = dataset.overlaps.map((o) => ({
      project_id_a: o.project_id_a,
      project_id_b: o.project_id_b,
      distance_km: o.distance_km,
      distance_mi: o.distance_mi,
      tier: o.tier,
      day_gap: o.day_gap,
      confidence: o.confidence,
    }));
    // insert in chunks to stay well under any request size limit
    const CHUNK = 500;
    for (let i = 0; i < overlapRows.length; i += CHUNK) {
      const { error } = await supabase.from("overlaps").insert(overlapRows.slice(i, i + CHUNK));
      if (error) throw error;
    }
  }

  console.log("Replacing cost_impact table...");
  {
    const { error: delErr } = await supabase.from("cost_impact").delete().neq("id", -1);
    if (delErr) throw delErr;

    // Look up the overlap row id for the pair this estimate is about, so
    // the UI can join cost_impact -> overlaps if it wants to.
    const { data: matchedOverlap } = await supabase
      .from("overlaps")
      .select("id")
      .eq("project_id_a", costImpact.overlap.desc_project_id)
      .eq("project_id_b", costImpact.overlap.gpc_project_id)
      .limit(1)
      .maybeSingle();

    const ci = costImpact;
    const { error } = await supabase.from("cost_impact").insert({
      overlap_id: matchedOverlap?.id ?? null,
      desc_project_title: ci.overlap.desc_project,
      gpc_project_titles: ci.overlap.gpc_projects,
      distance_mi: ci.overlap.distance_mi,
      tier: ci.overlap.tier,
      day_gap: ci.overlap.day_gap,
      location_note: ci.overlap.location_note,
      desc_total_cost_usd: ci.known_costs.desc_total_project_cost_usd,
      desc_cost_source: ci.known_costs.desc_cost_source,
      gpc_total_cost_usd: ci.known_costs.gpc_total_project_cost_usd,
      gpc_cost_note: ci.known_costs.gpc_cost_note,
      savings_pct_low: ci.illustrative_savings_estimate.savings_pct_range[0],
      savings_pct_high: ci.illustrative_savings_estimate.savings_pct_range[1],
      savings_usd_low: ci.illustrative_savings_estimate.savings_usd_low,
      savings_usd_high: ci.illustrative_savings_estimate.savings_usd_high,
      benchmark_source: ci.illustrative_savings_estimate.benchmark_source,
      narrative: ci.the_actual_problem_this_illustrates,
    });
    if (error) throw error;
  }

  console.log("Seed complete.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
