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
    <div className="mt-2 pt-2 border-t border-[var(--border)]" onClick={(e) => e.stopPropagation()}>
      {localNotes.length === 0 && (
        <div className="text-[11px] text-[var(--muted)] italic">No coordination notes yet.</div>
      )}
      <div className="flex flex-col gap-1.5">
        {localNotes.map((n) => (
          <div key={n.id} className="text-[11.5px] bg-[#0f1428] rounded-md px-2 py-1.5">
            <span className="text-[var(--muted)]">{n.author_label} &middot; {new Date(n.created_at).toLocaleDateString()}</span>
            <div>{n.body}</div>
          </div>
        ))}
      </div>
      {currentUserId ? (
        <div className="mt-2 flex gap-1.5">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Add a coordination note..."
            className="flex-1 bg-[#0f1428] border border-[var(--border)] rounded-md px-2 py-1 text-[11.5px] text-[var(--foreground)]"
            maxLength={1000}
          />
          <button
            onClick={submit}
            disabled={submitting || !draft.trim()}
            className="text-[11.5px] px-2.5 rounded-md bg-lime-600 disabled:opacity-40"
          >
            Post
          </button>
        </div>
      ) : (
        <div className="text-[11px] text-[var(--muted)] mt-2">
          <Link href="/login" className="underline">
            Sign in
          </Link>{" "}
          to leave a coordination note.
        </div>
      )}
      {error && <div className="text-[11px] text-red-400 mt-1">{error}</div>}
    </div>
  );
}
