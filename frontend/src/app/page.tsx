import { createClient } from "@/lib/supabase/server";
import { getCostImpact, getOverlaps, getPlannerNotes, getProjects } from "@/lib/data";
import Dashboard from "@/components/Dashboard";
import HeaderAuth from "@/components/HeaderAuth";

export default async function Home() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const [projects, overlaps, costImpact, notes] = await Promise.all([
    getProjects(),
    getOverlaps(),
    getCostImpact(),
    getPlannerNotes(),
  ]);

  return (
    <div className="flex flex-col h-screen">
      <header className="flex items-center justify-between px-5 py-3 border-b border-[var(--border)] bg-[var(--panel)]">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-md bg-[var(--accent)]/15 border border-[var(--accent)]/30 flex items-center justify-center">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M9 1L2.5 9h4L6 15l6.5-8h-4L9 1z" fill="var(--accent)" />
            </svg>
          </div>
          <div>
            <h1 className="text-[16px] font-semibold m-0 tracking-tight">Sentinel Utilities</h1>
            <div className="text-[12px] text-[var(--muted)] leading-tight">
              Dominion Energy South Carolina &times; Georgia Power &mdash; construction coordination
            </div>
          </div>
        </div>
        <div className="flex items-center gap-5">
          <div className="flex gap-4 text-[11.5px] text-[var(--muted)] font-mono-tab">
            <span className="flex items-center gap-1.5">
              <i className="inline-block w-2 h-2 rounded-full" style={{ background: "var(--desc-color)" }} />
              DESC &middot; SC
            </span>
            <span className="flex items-center gap-1.5">
              <i className="inline-block w-2 h-2 rounded-full" style={{ background: "var(--gpc-color)" }} />
              Georgia Power &middot; GA
            </span>
          </div>
          <HeaderAuth email={user?.email ?? null} />
        </div>
      </header>
      <div className="flex-1 min-h-0">
        <Dashboard
          projects={projects}
          overlaps={overlaps}
          costImpact={costImpact}
          notes={notes}
          currentUserId={user?.id ?? null}
          currentUserLabel={user?.email ?? null}
        />
      </div>
    </div>
  );
}
