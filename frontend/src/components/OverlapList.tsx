"use client";

import { useMemo, useState } from "react";
import type { Overlap, PlannerNote, Project, Tier } from "@/lib/types";
import { TIER_COLOR, TIER_LABEL } from "@/lib/types";
import NoteThread from "@/components/NoteThread";

const TIERS: (Tier | "all")[] = ["all", "touching_crossing", "share_land", "share_logistics", "share_crews"];

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

  const rows = useMemo(
    () => overlaps.filter((o) => filter === "all" || o.tier === filter),
    [overlaps, filter]
  );

  return (
    <>
      <div className="flex gap-1.5 flex-wrap px-4 pb-3">
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
                  ? { borderColor: color, background: `color-mix(in srgb, ${color} 12%, transparent)`, color }
                  : { borderColor: "var(--border)", background: "var(--panel-2)", color: "var(--muted)" }
              }
            >
              {t === "all" ? "All" : TIER_LABEL[t]}
            </button>
          );
        })}
      </div>
      <div className="flex-1 overflow-y-auto px-2.5 pb-4 flex flex-col gap-2">
        {rows.map((o) => {
          const a = projectsById[o.project_id_a];
          const b = projectsById[o.project_id_b];
          if (!a || !b) return null;
          const isSelected = selectedId === o.id;
          const isExpanded = expandedId === o.id;
          const notes = notesByOverlap[o.id] ?? [];
          return (
            <div
              key={o.id}
              className="bg-[var(--panel-2)] border rounded-lg overflow-hidden cursor-pointer transition-colors"
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
                  <span className="font-mono-tab text-[16px] font-semibold">{o.distance_mi} mi</span>
                  <span
                    className="text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase tracking-wide"
                    style={{ background: `${TIER_COLOR[o.tier]}22`, color: TIER_COLOR[o.tier] }}
                  >
                    {TIER_LABEL[o.tier]}
                  </span>
                </div>
                <div className="flex flex-col gap-1">
                  <div className="text-[12.5px] leading-snug flex gap-1.5">
                    <span
                      className="shrink-0 font-mono-tab text-[10px] font-semibold px-1.5 rounded leading-[18px]"
                      style={{ background: "color-mix(in srgb, var(--desc-color) 15%, transparent)", color: "var(--desc-color)" }}
                    >
                      DESC
                    </span>
                    <span>{a.title}</span>
                  </div>
                  <div className="text-[12.5px] leading-snug flex gap-1.5">
                    <span
                      className="shrink-0 font-mono-tab text-[10px] font-semibold px-1.5 rounded leading-[18px]"
                      style={{ background: "color-mix(in srgb, var(--gpc-color) 15%, transparent)", color: "var(--gpc-color)" }}
                    >
                      GPC
                    </span>
                    <span>{b.title}</span>
                  </div>
                </div>
                <div className="flex justify-between items-center font-mono-tab text-[10.5px] text-[var(--muted)] mt-2 pt-2 border-t border-[var(--border)]">
                  <span>{o.day_gap != null ? `${o.day_gap}d apart` : "date n/a"}</span>
                  <span className="px-1.5 py-0.5 rounded bg-[var(--panel-3)]">{o.confidence.replace("_", " ")}</span>
                </div>
              </div>
              <button
                className="w-full text-left text-[11px] text-[var(--muted)] px-3 py-1.5 border-t border-[var(--border)] hover:text-[var(--foreground)] transition-colors"
                onClick={(e) => {
                  e.stopPropagation();
                  setExpandedId(isExpanded ? null : o.id);
                }}
              >
                {isExpanded ? "Hide notes" : `Notes (${notes.length})`}
              </button>
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
