"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
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
    <div className="h-screen flex items-center justify-center bg-[var(--background)]">
      <div className="w-full max-w-sm p-6 border border-[var(--border)] rounded-xl bg-[var(--panel)]">
        <h1 className="text-lg font-bold mb-1">Sign in to Gridlock</h1>
        <p className="text-sm text-[var(--muted)] mb-4">
          Sign in to leave coordination notes on flagged overlaps. Viewing the map and ranked list needs no
          account.
        </p>
        {sent ? (
          <p className="text-sm">Check {email} for a sign-in link.</p>
        ) : (
          <form onSubmit={sendLink} className="flex flex-col gap-2.5">
            <input
              type="email"
              required
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="bg-[var(--panel-2)] border border-[var(--border)] rounded-md px-3 py-2 text-sm"
            />
            <button
              type="submit"
              disabled={loading}
              className="bg-lime-600 rounded-md py-2 text-sm font-medium disabled:opacity-40"
            >
              {loading ? "Sending..." : "Send sign-in link"}
            </button>
            {error && <p className="text-xs text-red-400">{error}</p>}
          </form>
        )}
      </div>
    </div>
  );
}
