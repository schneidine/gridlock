"use client";

import { useCallback, useEffect, useState } from "react";
import { inkColor } from "@/lib/theme";
import { generateInsight, getCachedInsight } from "@/app/actions/insights";

const PRIORITY_COLOR: Record<string, string> = {
  high: "var(--tier-touch)",
  medium: "#f59e0b",
  low: "var(--muted)",
};

// Gemini is asked for "Label: text" lines; show the label bold and pull the
// priority word out of the verdict so it reads at a glance.
function InsightText({ text }: { text: string }) {
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  return (
    <div className="flex flex-col gap-2">
      {lines.map((line, i) => {
        const m = line.match(/^([A-Za-z ]{2,24}):\s*(.*)$/);
        if (!m) return <p key={i} className="m-0">{line}</p>;
        const [, label, body] = m;
        if (label.toLowerCase() === "verdict") {
          const p = body.match(/^(high|medium|low)\b[\s\w-]*?[.:,-]?\s*(.*)$/i);
          const level = p?.[1].toLowerCase();
          return (
            <p key={i} className="m-0">
              {level && (
                <span
                  className="inline-block mr-1.5 px-1.5 rounded text-[10px] font-semibold uppercase tracking-wide align-[1px]"
                  style={{ color: inkColor(PRIORITY_COLOR[level]), background: `color-mix(in srgb, ${PRIORITY_COLOR[level]} 15%, transparent)` }}
                >
                  {level} priority
                </span>
              )}
              {p ? p[2] : body}
            </p>
          );
        }
        return (
          <p key={i} className="m-0">
            <span className="font-semibold text-[var(--foreground)]">{label}:</span>{" "}
            <span className="text-[var(--muted)]">{body}</span>
          </p>
        );
      })}
    </div>
  );
}

export default function InsightPanel({ overlapId }: { overlapId: number }) {
  const [text, setText] = useState<string | null>(null);
  const [createdAt, setCreatedAt] = useState<string | null>(null);
  const [checkingCache, setCheckingCache] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    const result = await generateInsight(overlapId);
    setLoading(false);
    if ("error" in result) {
      setError(result.error);
      return;
    }
    setText(result.text);
    setCreatedAt(result.createdAt);
  }, [overlapId]);

  useEffect(() => {
    let cancelled = false;
    // Opening the panel is the "generate" click: show the cached summary if
    // there is one, otherwise ask Gemini straight away.
    getCachedInsight(overlapId)
      .catch(() => null)
      .then((cached) => {
        if (cancelled) return;
        setCheckingCache(false);
        if (cached) {
          setText(cached.text);
          setCreatedAt(cached.createdAt);
        } else {
          run();
        }
      });
    return () => {
      cancelled = true;
    };
  }, [overlapId, run]);

  return (
    <div className="flex flex-col gap-2" onClick={(e) => e.stopPropagation()}>
      {text && (
        <div className="text-[11.5px] leading-relaxed bg-[var(--panel)] border border-[var(--border)] rounded-md px-2.5 py-2">
          <InsightText text={text} />
        </div>
      )}
      {(checkingCache || loading) && (
        <div className="text-[11.5px] text-[var(--muted)] animate-pulse">
          {checkingCache ? "Loading…" : "Generating insights…"}
        </div>
      )}
      <div className="flex items-center gap-2 text-[10.5px] text-[var(--muted)]">
        {text && createdAt && !loading && <span>Generated {new Date(createdAt).toLocaleDateString()}</span>}
        {text && !loading && (
          <button onClick={run} className="underline hover:text-[var(--foreground)] transition-colors">
            Regenerate
          </button>
        )}
        <span className="ml-auto flex items-center gap-1">
          <svg width="10" height="10" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
            <path d="M8 0l1.8 5.2L15 7l-5.2 1.8L8 14l-1.8-5.2L1 7l5.2-1.8z" />
          </svg>
          Powered by Gemini
        </span>
      </div>
      {error && <div className="text-[11px] text-[var(--tier-touch)]">{error}</div>}
    </div>
  );
}
