"use client";

import dynamic from "next/dynamic";
import type { Project } from "@/lib/types";

// Leaflet touches `window` on import, so the map must never render on the
// server -- ssr:false is required here, not just an optimization.
const GridlockMap = dynamic(() => import("@/components/GridlockMap"), { ssr: false });

export default function CompanyMap({ projects }: { projects: Project[] }) {
  return <GridlockMap projects={projects} flagCountByProject={{}} selectedOverlap={null} />;
}
