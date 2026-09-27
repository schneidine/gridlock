"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function sendLink(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const supabase = createClient();
    const { error: err } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${window.location.origin}/auth/confirm` },
    });
    setLoading(false);
    if (err) {
      setError(err.message);
      return;
    }
    setSent(true);
  }

  return (
    <div className="h-screen flex items-center justify-center bg-[var(--background)] px-4">
      <div className="w-full max-w-sm p-6 border border-[var(--border)] rounded-lg bg-[var(--panel)]">
        <button
          type="button"
          onClick={() => router.back()}
          className="mb-4 text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors flex items-center gap-1"
        >
          ← Back
        </button>
        <h1 className="text-lg font-semibold mb-1 tracking-tight">Sign in to Gridlock</h1>
        <p className="text-sm text-[var(--muted)] mb-5">
          Sign in to leave coordination notes on flagged overlaps. Viewing the map and ranked list needs no
          account.
        </p>
        {sent ? (
          <p className="text-sm">Check {email} for a sign-in link.</p>
        ) : (
          <form onSubmit={sendLink} className="flex flex-col gap-2.5">
            <label htmlFor="login-email" className="text-xs text-[var(--muted)]">
              Work email
            </label>
            <input
              id="login-email"
              type="email"
              required
              placeholder="you@utility.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="bg-[var(--panel-2)] border border-[var(--border)] rounded-md px-3 py-2 text-sm placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--accent)]"
            />
            <button
              type="submit"
              disabled={loading}
              className="bg-[var(--accent)] text-[var(--background)] hover:bg-[var(--accent-strong)] rounded-md py-2 text-sm font-medium disabled:opacity-40 transition-colors"
            >
              {loading ? "Sending…" : "Send sign-in link"}
            </button>
            {error && <p className="text-xs text-[var(--tier-touch)]">{error}</p>}
          </form>
        )}
      </div>
    </div>
  );
}
