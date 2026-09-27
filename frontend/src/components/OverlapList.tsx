"use client";

import { useMemo, useState } from "react";
import type { Confidence, Overlap, PlannerNote, Project, Tier } from "@/lib/types";
import { TIER_COLOR, TIER_LABEL, overlapScore } from "@/lib/types";
import { utilityStyle } from "@/lib/utilities";
import NoteThread from "@/components/NoteThread";
import InsightPanel from "@/components/InsightPanel";

const TIERS: (Tier | "all")[] = ["all", "shared_substation", "same_window", "schedules_apart"];

const CONF_RANK: Record<Confidence, number> = { confirmed: 0, low_confidence: 1 };

// A pair is only as trustworthy as its least-certain location, so flag the
// weaker of the two. Confirmed pairs get no tag to keep the list quiet.
const CONF_TAG: Partial<Record<Confidence, { label: string; title: string }>> = {
  low_confidence: { label: "est. location", title: "At least one project's location could not be fully confirmed, so the distance is approximate" },
};

function weakerConfidence(a: Project, b: Project): Confidence {
  const ca = a.geo_confidence ?? "low_confidence";
  const cb = b.geo_confidence ?? "low_confidence";
  return CONF_RANK[ca] >= CONF_RANK[cb] ? ca : cb;
}

export default function OverlapList({
  overlaps,
  projectsById,
  notesByOverlap,
  currentUserId,
  currentUserLabel,
  onSelect,
}: {
  overlaps: Overlap[];
  projectsById: Record<string, Project>;
  notesByOverlap: Record<number, PlannerNote[]>;
  currentUserId: string | null;
  currentUserLabel: string | null;
  onSelect: (overlap: Overlap) => void;
}) {
  const [filter, setFilter] = useState<Tier | "all">("all");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [insightId, setInsightId] = useState<number | null>(null);

  // Rank over the full list by the pipeline's score so a pair keeps its rank
  // number when a category filter is applied.
  const ranked = useMemo(
    () =>
      [...overlaps]
        .sort((x, y) => overlapScore(y) - overlapScore(x) || x.distance_km - y.distance_km)
        .map((o, i) => ({ o, rank: i + 1 })),
    [overlaps]
  );

  const rows = useMemo(
    () => ranked.filter(({ o }) => filter === "all" || o.tier === filter),
    [ranked, filter]
  );

  return (
    <>
      <div className="shrink-0 flex gap-1.5 flex-wrap px-4 pb-3">
        {TIERS.map((t) => {
          const active = filter === t;
          const color = t === "all" ? "var(--accent)" : TIER_COLOR[t];
          return (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className="text-[11px] font-medium px-2.5 py-1 rounded-full border transition-colors"
              style={
                active
                  ? { borderColor: color, background: `color-mix(in srgb, ${color} 12%, transparent)`, color: inkColor(color) }
                  : { borderColor: "var(--border)", background: "var(--panel-2)", color: "var(--muted)" }
              }
            >
              {t === "all" ? "All" : TIER_LABEL[t]}
            </button>
          );
        })}
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto px-2.5 pb-4 flex flex-col gap-2">
        {rows.map(({ o, rank }) => {
          const a = projectsById[o.project_id_a];
          const b = projectsById[o.project_id_b];
          if (!a || !b) return null;
          const isSelected = selectedId === o.id;
          const isExpanded = expandedId === o.id;
          const showInsight = insightId === o.id;
          const confTag = CONF_TAG[weakerConfidence(a, b)];
          const notes = notesByOverlap[o.id] ?? [];
          return (
            <div
              key={o.id}
              className="shrink-0 bg-[var(--panel-2)] border rounded-lg overflow-hidden cursor-pointer transition-colors"
              style={{ borderColor: isSelected ? "var(--accent)" : "var(--border)" }}
            >
              <div
                className="p-3"
                onClick={() => {
                  setSelectedId(o.id);
                  onSelect(o);
                }}
              >
                <div className="flex justify-between items-center mb-2">
                  <div className="flex items-baseline gap-2.5">
                    <span
                      className="font-mono-tab text-[13px] font-semibold"
                      style={{ color: rank <= 3 ? "var(--accent-strong)" : "var(--muted)" }}
                    >
                      #{rank}
                    </span>
                    <span className="font-mono-tab text-[16px] font-semibold">{o.distance_mi} mi</span>
                    {confTag && (
                      <span className="text-[10.5px] text-[var(--muted)] italic" title={confTag.title}>
                        {confTag.label}
                      </span>
                    )}
                  </div>
                  <span
                    className="text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase tracking-wide"
                    style={{ background: `${TIER_COLOR[o.tier]}22`, color: inkColor(TIER_COLOR[o.tier]) }}
                  >
                    {TIER_LABEL[o.tier]}
                  </span>
                </div>
                <div className="flex flex-col gap-1">
                  <ProjectLine p={a} />
                  <ProjectLine p={b} />
                </div>
              </div>
              <div className="flex border-t border-[var(--border)]">
                <button
                  className="flex-1 text-left text-[11px] text-[var(--muted)] px-3 py-1.5 hover:text-[var(--foreground)] transition-colors"
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedId(isExpanded ? null : o.id);
                  }}
                >
                  {isExpanded ? "Hide notes" : `Notes (${notes.length})`}
                </button>
                <button
                  className="flex items-center gap-1 text-[11px] font-semibold px-3 py-1.5 border-l border-[var(--border)] transition-colors hover:brightness-125"
                  style={{
                    color: "var(--accent-strong)",
                    background: showInsight
                      ? "color-mix(in srgb, var(--accent) 22%, transparent)"
                      : "color-mix(in srgb, var(--accent) 10%, transparent)",
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    setInsightId(showInsight ? null : o.id);
                  }}
                >
                  <svg width="11" height="11" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
                    <path d="M8 0l1.8 5.2L15 7l-5.2 1.8L8 14l-1.8-5.2L1 7l5.2-1.8z" />
                  </svg>
                  {showInsight ? "Hide AI Insights" : "Generate AI Insights"}
                </button>
              </div>
              {showInsight && (
                <div className="px-3 pb-3">
                  <InsightPanel overlapId={o.id} />
                </div>
              )}
              {isExpanded && (
                <div className="px-3 pb-3">
                  <NoteThread
                    overlapId={o.id}
                    notes={notes}
                    currentUserId={currentUserId}
                    currentUserLabel={currentUserLabel}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </>
  );
}

function ProjectLine({ p }: { p: Project }) {
  const { short, color } = utilityStyle(p.utility);
  return (
    <div className="text-[12.5px] leading-snug flex gap-1.5">
      <span
        className="shrink-0 font-mono-tab text-[10px] font-semibold px-1.5 rounded leading-[18px]"
        style={{ background: `color-mix(in srgb, ${color} 15%, transparent)`, color }}
      >
        {short}
      </span>
      <span>{p.title}</span>
    </div>
  );
}
