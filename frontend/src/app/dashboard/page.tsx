import { cookies } from "next/headers";
import { mockSignOut } from "@/app/actions/mock-auth";
import { getOverlaps, getProjects } from "@/lib/data";
import CompanyMap from "@/components/CompanyMap";

const ORG_NAMES: Record<string, string> = {
  desc: "Dominion Energy South Carolina (DESC)",
  gpc: "Georgia Power",
};

// Must match Project.utility exactly.
const ORG_UTILITY_NAMES: Record<string, string> = {
  desc: "Dominion Energy South Carolina",
  gpc: "Georgia Power",
};

export default async function DashboardPage() {
  const cookieStore = await cookies();
  const orgId = cookieStore.get("gridlock_org")?.value;
  const companyName = orgId ? ORG_NAMES[orgId] ?? orgId : null;
  const utilityName = orgId ? ORG_UTILITY_NAMES[orgId] : null;

  const allProjects = utilityName ? await getProjects() : [];
  const projects = allProjects.filter((p) => p.utility === utilityName);

  const allOverlaps = utilityName ? await getOverlaps() : [];
  const projectsById: Record<string, (typeof allProjects)[number]> = {};
  for (const p of allProjects) projectsById[p.project_id] = p;

  const myOverlaps = allOverlaps.filter((o) => {
    const a = projectsById[o.project_id_a];
    const b = projectsById[o.project_id_b];
    return a?.utility === utilityName || b?.utility === utilityName;
  });

  const flagCountByProject: Record<string, number> = {};
  for (const o of myOverlaps) {
    flagCountByProject[o.project_id_a] = (flagCountByProject[o.project_id_a] ?? 0) + 1;
    flagCountByProject[o.project_id_b] = (flagCountByProject[o.project_id_b] ?? 0) + 1;
  }

  // Show my own projects plus the other utility's project in any overlap
  // that touches one of mine, so a flagged pair still makes sense on the
  // map -- unrelated projects from the other utility stay hidden.
  const mapProjectIds = new Set(projects.map((p) => p.project_id));
  for (const o of myOverlaps) {
    mapProjectIds.add(o.project_id_a);
    mapProjectIds.add(o.project_id_b);
  }
  const mapProjects = allProjects.filter((p) => mapProjectIds.has(p.project_id));

  return (
    <div className="flex flex-col h-screen">
      <header className="flex items-center justify-between px-5 py-3 border-b border-[var(--border)] bg-[var(--panel)]">
        <div>
          <h1 className="text-[16px] font-semibold m-0 tracking-tight">
            {companyName ? `Welcome, ${companyName}` : "Hello"}
          </h1>
          {companyName && (
            <div className="text-[12px] text-[var(--muted)] leading-tight">
              {projects.length} project{projects.length === 1 ? "" : "s"} &middot; {myOverlaps.length} flagged
              overlap{myOverlaps.length === 1 ? "" : "s"}
            </div>
          )}
        </div>
        {companyName && (
          <form action={mockSignOut}>
            <button
              type="submit"
              className="text-xs px-3 py-1.5 rounded-md border border-[var(--border)] hover:border-[var(--border-strong)] transition-colors"
            >
              Sign out
            </button>
          </form>
        )}
      </header>
      <div className="flex-1 min-h-0">
        {companyName ? (
          <CompanyMap projects={mapProjects} myUtilityName={utilityName!} flagCountByProject={flagCountByProject} />
        ) : (
          <div className="h-full flex items-center justify-center text-[var(--muted)]">
            Sign in to see your company&apos;s sites.
          </div>
        )}
      </div>
    </div>
  );
}
