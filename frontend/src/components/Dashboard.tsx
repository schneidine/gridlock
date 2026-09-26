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
        <GridlockMap projects={projects} selectedOverlap={selectedPair} />
      </div>
      <div className="border-l border-[var(--border)] bg-[var(--panel)] overflow-y-auto flex flex-col">
        <div className="flex gap-2.5 p-2.5 border-b border-[var(--border)]">
          <Stat n={projects.length} label="Projects" />
          <Stat n={overlaps.length} label="Flagged Overlaps" />
          <Stat n={highPriorityCount} label="High-Priority" />
        </div>
        {costImpact[0] && <CostImpactPanel ci={costImpact[0]} />}
        <h2 className="text-[13px] uppercase tracking-wide text-[var(--muted)] px-4 pt-3.5 pb-1.5 m-0">
          Coordination Opportunities
        </h2>
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

function Stat({ n, label }: { n: number; label: string }) {
  return (
    <div className="flex-1 text-center">
      <div className="text-xl font-bold">{n}</div>
      <div className="text-[10.5px] uppercase text-[var(--muted)]">{label}</div>
    </div>
  );
}
