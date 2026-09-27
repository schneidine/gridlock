import Link from "next/link";
import { signOut } from "@/app/actions/auth";

export default function HeaderAuth({ email }: { email: string | null }) {
  if (!email) {
    return (
      <Link
        href="/login"
        className="text-xs font-medium px-3 py-1.5 rounded-md bg-[var(--accent)] text-[var(--background)] hover:bg-[var(--accent-strong)] transition-colors"
      >
        Sign in
      </Link>
    );
  }
  return (
    <div className="flex items-center gap-2.5">
      <Link
        href="/dashboard"
        className="text-xs font-medium px-3 py-1.5 rounded-md border border-[var(--border)] hover:border-[var(--border-strong)] transition-colors"
      >
        Dashboard
      </Link>
      <form action={signOut} className="flex items-center gap-2.5">
        <span className="text-xs text-[var(--muted)]">{email}</span>
        <button className="text-xs px-3 py-1.5 rounded-md border border-[var(--border)] hover:border-[var(--border-strong)] transition-colors">
          Sign out
        </button>
      </form>
    </div>
  );
}
