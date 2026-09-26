"use client";

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import type { CostImpact, Overlap, PlannerNote, Project } from "@/lib/types";
import OverlapList from "@/components/OverlapList";
import CostImpactPanel from "@/components/CostImpactPanel";

// Leaflet touches `window` on import, so the map must never render on the
// server -- ssr:false is required here, not just an optimization.
const GridlockMap = dynamic(() => import("@/components/GridlockMap"), { ssr: false });

export default function Dashboard({
  projects,
  overlaps,
  costImpact,
  notes,
  currentUserId,
  currentUserLabel,
}: {
  projects: Project[];
  overlaps: Overlap[];
  costImpact: CostImpact[];
  notes: PlannerNote[];
  currentUserId: string | null;
  currentUserLabel: string | null;
}) {
  const [selectedOverlap, setSelectedOverlap] = useState<Overlap | null>(null);

  const projectsById = useMemo(() => {
    const map: Record<string, Project> = {};
    for (const p of projects) map[p.project_id] = p;
    return map;
  }, [projects]);

  const flagCountByProject = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const o of overlaps) {
      counts[o.project_id_a] = (counts[o.project_id_a] ?? 0) + 1;
      counts[o.project_id_b] = (counts[o.project_id_b] ?? 0) + 1;
    }
    return counts;
  }, [overlaps]);

  const notesByOverlap = useMemo(() => {
    const map: Record<number, PlannerNote[]> = {};
    for (const n of notes) {
      (map[n.overlap_id] ??= []).push(n);
    }
    return map;
  }, [notes]);

  const selectedPair =
    selectedOverlap && projectsById[selectedOverlap.project_id_a] && projectsById[selectedOverlap.project_id_b]
      ? { a: projectsById[selectedOverlap.project_id_a], b: projectsById[selectedOverlap.project_id_b] }
      : null;

  const highPriorityCount = overlaps.filter(
    (o) => o.tier === "touching_crossing" || o.tier === "share_land"
  ).length;

  return (
    <div className="grid grid-cols-[1fr_420px] grid-rows-[1fr] h-full">
      <div className="h-full w-full">
        <GridlockMap projects={projects} flagCountByProject={flagCountByProject} selectedOverlap={selectedPair} />
      </div>
      <div className="border-l border-[var(--border)] bg-[var(--panel)] overflow-y-auto flex flex-col">
        <div className="grid grid-cols-3 gap-px bg-[var(--border)] border-b border-[var(--border)]">
          <Stat n={projects.length} label="Projects" />
          <Stat n={overlaps.length} label="Flagged" />
          <Stat n={highPriorityCount} label="High-priority" accent />
        </div>
        {costImpact[0] && <CostImpactPanel ci={costImpact[0]} />}
        <div className="px-4 pt-4 pb-2.5 flex flex-col gap-1">
          <h2 className="text-[12px] uppercase tracking-[0.08em] text-[var(--muted)] font-medium m-0">
            Coordination Opportunities
          </h2>
          <p className="text-[11.5px] text-[var(--muted)] leading-snug m-0">
            Ranked by how close the projects are (tier), then how close their build schedules are, then exact
            distance.
          </p>
        </div>
        <OverlapList
          overlaps={overlaps}
          projectsById={projectsById}
          notesByOverlap={notesByOverlap}
          currentUserId={currentUserId}
          currentUserLabel={currentUserLabel}
          onSelect={setSelectedOverlap}
        />
      </div>
    </div>
  );
}

function Stat({ n, label, accent }: { n: number; label: string; accent?: boolean }) {
  return (
    <div className="bg-[var(--panel)] px-3 py-3 flex flex-col items-center gap-0.5">
      <div
        className="font-mono-tab text-[20px] font-semibold leading-none"
        style={{ color: accent && n > 0 ? "var(--tier-touch)" : "var(--foreground)" }}
      >
        {n}
      </div>
      <div className="text-[10px] uppercase tracking-wide text-[var(--muted)]">{label}</div>
    </div>
  );
}
