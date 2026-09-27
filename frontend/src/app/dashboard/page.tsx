import { cookies } from "next/headers";
import { mockSignOut } from "@/app/actions/mock-auth";
import { getProjects } from "@/lib/data";
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

  const projects = utilityName ? (await getProjects()).filter((p) => p.utility === utilityName) : [];

  return (
    <div className="flex flex-col h-screen">
      <header className="flex items-center justify-between px-5 py-3 border-b border-[var(--border)] bg-[var(--panel)]">
        <div>
          <h1 className="text-[16px] font-semibold m-0 tracking-tight">
            {companyName ? `Welcome, ${companyName}` : "Hello"}
          </h1>
          {companyName && (
            <div className="text-[12px] text-[var(--muted)] leading-tight">
              {projects.length} of your project{projects.length === 1 ? "" : "s"}
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
          <CompanyMap projects={projects} myUtilityName={utilityName!} />
        ) : (
          <div className="h-full flex items-center justify-center text-[var(--muted)]">
            Sign in to see your company&apos;s sites.
          </div>
        )}
      </div>
    </div>
  );
}
