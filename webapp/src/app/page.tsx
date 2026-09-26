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
      <header className="flex items-center justify-between px-5 py-3.5 border-b border-[var(--border)] bg-[var(--panel)]">
        <div>
          <h1 className="text-[17px] font-bold m-0">Gridlock</h1>
          <div className="text-[12.5px] text-[var(--muted)] mt-0.5">
            Dominion Energy South Carolina &times; Georgia Power &mdash; planned construction coordination
          </div>
        </div>
        <div className="flex items-center gap-5">
          <div className="flex gap-4 text-xs text-[var(--muted)]">
            <span className="flex items-center gap-1.5">
              <i className="inline-block w-2.5 h-2.5 rounded-full bg-blue-600" />
              DESC (SC)
            </span>
            <span className="flex items-center gap-1.5">
              <i className="inline-block w-2.5 h-2.5 rounded-full bg-orange-600" />
              Georgia Power (GA)
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
