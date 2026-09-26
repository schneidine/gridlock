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
      <div className="flex gap-1.5 flex-wrap px-4 pb-2.5">
        {TIERS.map((t) => (
          <button
            key={t}
            onClick={() => setFilter(t)}
            className={`text-[11.5px] px-2.5 py-1 rounded-md border ${
              filter === t ? "border-lime-500 bg-[#1c2440]" : "border-[var(--border)] bg-[var(--panel-2)]"
            }`}
          >
            {t === "all" ? "All" : TIER_LABEL[t]}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto px-2.5 pb-4">
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
              className={`bg-[var(--panel-2)] border rounded-xl p-3 m-1.5 cursor-pointer transition-colors ${
                isSelected ? "border-orange-500" : "border-[var(--border)] hover:border-[#3b4374]"
              }`}
            >
              <div
                onClick={() => {
                  setSelectedId(o.id);
                  onSelect(o);
                }}
              >
                <div className="flex justify-between items-baseline mb-1.5">
                  <span className="text-[15px] font-bold">{o.distance_mi} mi</span>
                  <span
                    className="text-[10.5px] px-1.5 py-0.5 rounded-full font-semibold uppercase tracking-wide"
                    style={{ background: `${TIER_COLOR[o.tier]}22`, color: TIER_COLOR[o.tier] }}
                  >
                    {TIER_LABEL[o.tier]}
                  </span>
                </div>
                <div className="text-[12.5px] leading-relaxed my-0.5">
                  <b className="text-blue-500">DESC</b> {a.title}
                </div>
                <div className="text-[12.5px] leading-relaxed my-0.5">
                  <b className="text-orange-500">GPC</b> {b.title}
                </div>
                <div className="flex justify-between text-[11px] text-[var(--muted)] mt-1.5">
                  <span>{o.day_gap != null ? `${o.day_gap}d apart` : "date n/a"}</span>
                  <span className="px-1.5 rounded bg-[#1c2440]">{o.confidence.replace("_", " ")}</span>
                </div>
              </div>
              <button
                className="text-[11px] text-[var(--muted)] mt-2 underline"
                onClick={(e) => {
                  e.stopPropagation();
                  setExpandedId(isExpanded ? null : o.id);
                }}
              >
                {isExpanded ? "hide notes" : `notes (${notes.length})`}
              </button>
              {isExpanded && (
                <NoteThread
                  overlapId={o.id}
                  notes={notes}
                  currentUserId={currentUserId}
                  currentUserLabel={currentUserLabel}
                />
              )}
            </div>
          );
        })}
      </div>
    </>
  );
}
