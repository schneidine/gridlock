import Link from "next/link";
import { mockSignIn } from "@/app/actions/mock-auth";

const ORG_OPTIONS = [
  { id: "desc", label: "Dominion Energy South Carolina (DESC)" },
  { id: "gpc", label: "Georgia Power (GPC)" },
];

export default function LoginPage() {
  return (
    <div className="h-screen flex items-center justify-center bg-[var(--background)] px-4">
      <div className="w-full max-w-sm p-6 border border-[var(--border)] rounded-lg bg-[var(--panel)]">
        <Link
          href="/"
          className="mb-4 text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors flex items-center gap-1"
        >
          ← Back
        </Link>
        <h1 className="text-lg font-semibold mb-1 tracking-tight">Sign in to Sentinel Utilities</h1>
        <p className="text-sm text-[var(--muted)] mb-5">
          Pick your company to see a dashboard focused on your own projects and the overlaps that involve you.
        </p>
        <form action={mockSignIn} className="flex flex-col gap-2.5">
          <label htmlFor="login-org" className="text-xs text-[var(--muted)]">
            Company
          </label>
          <select
            id="login-org"
            name="org_id"
            defaultValue={ORG_OPTIONS[0].id}
            className="bg-[var(--panel-2)] border border-[var(--border)] rounded-md px-3 py-2 text-sm focus:outline-none focus:border-[var(--accent)]"
          >
            {ORG_OPTIONS.map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </select>
          <button
            type="submit"
            className="bg-[var(--accent)] text-[var(--background)] hover:bg-[var(--accent-strong)] rounded-md py-2 text-sm font-medium transition-colors"
          >
            Sign in
          </button>
        </form>
      </div>
    </div>
  );
}
