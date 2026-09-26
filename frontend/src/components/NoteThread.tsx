"use client";

import { useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import type { PlannerNote } from "@/lib/types";

export default function NoteThread({
  overlapId,
  notes,
  currentUserId,
  currentUserLabel,
}: {
  overlapId: number;
  notes: PlannerNote[];
  currentUserId: string | null;
  currentUserLabel: string | null;
}) {
  const [localNotes, setLocalNotes] = useState(notes);
  const [draft, setDraft] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!draft.trim() || !currentUserId) return;
    setSubmitting(true);
    setError(null);
    const supabase = createClient();
    const { data, error: err } = await supabase
      .from("planner_notes")
      .insert({
        overlap_id: overlapId,
        user_id: currentUserId,
        author_label: currentUserLabel ?? "planner",
        body: draft.trim(),
      })
      .select()
      .single();
    setSubmitting(false);
    if (err) {
      setError(err.message);
      return;
    }
    setLocalNotes((prev) => [...prev, data as PlannerNote]);
    setDraft("");
  }

  return (
    <div className="flex flex-col gap-2" onClick={(e) => e.stopPropagation()}>
      {localNotes.length === 0 && (
        <div className="text-[11px] text-[var(--muted)]">No coordination notes yet.</div>
      )}
      {localNotes.length > 0 && (
        <div className="flex flex-col gap-1.5">
          {localNotes.map((n) => (
            <div key={n.id} className="text-[11.5px] bg-[var(--panel)] border border-[var(--border)] rounded-md px-2.5 py-1.5">
              <div className="text-[10.5px] text-[var(--muted)] mb-0.5">
                {n.author_label} &middot; <span className="font-mono-tab">{new Date(n.created_at).toLocaleDateString()}</span>
              </div>
              <div>{n.body}</div>
            </div>
          ))}
        </div>
      )}
      {currentUserId ? (
        <div className="flex gap-1.5">
          <input
            id={`note-draft-${overlapId}`}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Add a coordination note…"
            className="flex-1 bg-[var(--panel)] border border-[var(--border)] rounded-md px-2.5 py-1.5 text-[11.5px] text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--accent)]"
            maxLength={1000}
          />
          <button
            onClick={submit}
            disabled={submitting || !draft.trim()}
            className="text-[11.5px] font-medium px-3 rounded-md bg-[var(--accent)] text-[var(--background)] hover:bg-[var(--accent-strong)] disabled:opacity-40 transition-colors"
          >
            {submitting ? "Posting…" : "Post"}
          </button>
        </div>
      ) : (
        <div className="text-[11px] text-[var(--muted)]">
          <Link href="/login" className="underline hover:text-[var(--foreground)]">
            Sign in
          </Link>{" "}
          to leave a coordination note.
        </div>
      )}
      {error && <div className="text-[11px] text-[var(--tier-touch)]">{error}</div>}
    </div>
  );
}
