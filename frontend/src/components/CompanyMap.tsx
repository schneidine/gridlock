"use client";

import dynamic from "next/dynamic";
import type { Project } from "@/lib/types";

// Leaflet touches `window` on import, so the map must never render on the
// server -- ssr:false is required here, not just an optimization.
const GridlockMap = dynamic(() => import("@/components/GridlockMap"), { ssr: false });

export default function CompanyMap({ projects, myUtilityName }: { projects: Project[]; myUtilityName: string }) {
  const otherUtilityName =
    myUtilityName === "Dominion Energy South Carolina" ? "Georgia Power" : "Dominion Energy South Carolina";
  return (
    <GridlockMap
      projects={projects}
      flagCountByProject={{}}
      selectedOverlap={null}
      hideUtility={otherUtilityName}
    />
  );
}
