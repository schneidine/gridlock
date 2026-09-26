import Link from "next/link";
import { signOut } from "@/app/actions/auth";

export default function HeaderAuth({ email }: { email: string | null }) {
  if (!email) {
    return (
      <Link
        href="/login"
        className="text-xs px-3 py-1.5 rounded-md border border-[var(--border)] hover:border-[#3b4374]"
      >
        Sign in
      </Link>
    );
  }
  return (
    <form action={signOut} className="flex items-center gap-2">
      <span className="text-xs text-[var(--muted)]">{email}</span>
      <button className="text-xs px-3 py-1.5 rounded-md border border-[var(--border)] hover:border-[#3b4374]">
        Sign out
      </button>
    </form>
  );
}
