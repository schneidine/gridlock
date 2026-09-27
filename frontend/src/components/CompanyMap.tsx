"use client";

import dynamic from "next/dynamic";
import type { Project } from "@/lib/types";

// Leaflet touches `window` on import, so the map must never render on the
// server -- ssr:false is required here, not just an optimization.
const SentinelMap = dynamic(() => import("@/components/SentinelMap"), { ssr: false });

export default function CompanyMap({
  projects,
  flagCountByProject,
}: {
  projects: Project[];
  myUtilityName: string;
  flagCountByProject: Record<string, number>;
}) {
  // Both utilities' colors are meaningful here now -- a flagged overlap
  // pulls in the other company's counterpart project too -- so the legend
  // is left showing both, unlike the earlier own-projects-only view.
  return <SentinelMap projects={projects} flagCountByProject={flagCountByProject} selectedOverlap={null} />;
}
