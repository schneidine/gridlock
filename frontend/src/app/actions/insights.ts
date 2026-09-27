"use server";

import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import type { CostImpact, Overlap, Project } from "@/lib/types";
import { buildPrompt } from "@/lib/insightPrompt";

const GEMINI_MODEL = process.env.GEMINI_MODEL ?? "gemini-3.8-flash";

export type InsightResult = { text: string; createdAt: string } | { error: string };

// Returns the cached summary for a pair, or null if none has been generated
// yet (or the cache table hasn't been created).
export async function getCachedInsight(overlapId: number): Promise<{ text: string; createdAt: string } | null> {
  const supabase = await createClient();
  const { data } = await supabase
    .from("overlap_insights")
    .select("body, created_at")
    .eq("overlap_id", overlapId)
    .maybeSingle();
  return data ? { text: data.body, createdAt: data.created_at } : null;
}

// Takes only the overlap id and loads the pair server-side, so the client
// can't steer the prompt or spend the Gemini key on arbitrary text.
export async function generateInsight(overlapId: number): Promise<InsightResult> {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) return { error: "GEMINI_API_KEY is not set on the server." };

  const supabase = await createClient();
  const { data: overlap, error: overlapErr } = await supabase
    .from("overlaps")
    .select("*")
    .eq("id", overlapId)
    .single();
  if (overlapErr || !overlap) return { error: "Match not found." };
  const o = overlap as Overlap;

  const [{ data: projects }, { data: costRows }] = await Promise.all([
    supabase.from("projects").select("*").in("project_id", [o.project_id_a, o.project_id_b]),
    supabase.from("cost_impact").select("*").eq("overlap_id", overlapId),
  ]);
  const a = (projects as Project[] | null)?.find((p) => p.project_id === o.project_id_a);
  const b = (projects as Project[] | null)?.find((p) => p.project_id === o.project_id_b);
  if (!a || !b) return { error: "Project details not found." };
  const ci = (costRows as CostImpact[] | null)?.[0];

  const prompt = buildPrompt(o, a, b, ci);

  let res: Response;
  try {
    res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-goog-api-key": apiKey },
        body: JSON.stringify({
          contents: [{ role: "user", parts: [{ text: prompt }] }],
          // Gemini 3 models spend output tokens on hidden reasoning first; a low
          // thinking level plus a roomy cap keeps the answer from being cut off.
          generationConfig: { temperature: 0.4, maxOutputTokens: 4096, thinkingConfig: { thinkingLevel: "low" } },
        }),
      }
    );
  } catch {
    return { error: "Could not reach Gemini." };
  }
  if (!res.ok) return { error: `Gemini request failed (${res.status}).` };

  const json = await res.json();
  const candidate = json?.candidates?.[0];
  const text: string = (candidate?.content?.parts ?? [])
    .map((p: { text?: string }) => p.text ?? "")
    .join("")
    .trim();
  if (!text) return { error: "Gemini returned an empty response." };
  // Don't cache a truncated answer; the next click should try again.
  if (candidate?.finishReason === "MAX_TOKENS") {
    return { text: `${text}…\n\n(Response was cut off — try Regenerate.)`, createdAt: new Date().toISOString() };
  }

  const { data: saved, error: cacheErr } = await createAdminClient()
    .from("overlap_insights")
    .upsert({ overlap_id: overlapId, body: text, model: GEMINI_MODEL, created_at: new Date().toISOString() })
    .select("created_at")
    .single();
  // A failed cache write shouldn't cost the user the answer they waited for.
  if (cacheErr) console.error("overlap_insights cache write failed:", cacheErr.message);
  return { text, createdAt: saved?.created_at ?? new Date().toISOString() };
}
