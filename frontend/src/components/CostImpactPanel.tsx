"use client";

import { useState } from "react";
import type { CostImpact } from "@/lib/types";

function fmtUsd(n: number | null) {
  if (n == null) return "n/a";
  return "$" + Math.round(n).toLocaleString("en-US");
}

export default function CostImpactPanel({ ci }: { ci: CostImpact }) {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const yrs = ci.day_gap != null ? (ci.day_gap / 365.25).toFixed(1) : null;

  return (
    <div
      className="shrink-0 m-3 mx-4 rounded-lg border"
      style={{
        borderColor: "color-mix(in srgb, var(--accent) 35%, var(--border))",
        background: "linear-gradient(180deg, color-mix(in srgb, var(--accent) 9%, var(--panel-2)) 0%, var(--panel-2) 100%)",
      }}
    >
      <button
        className="w-full flex items-center justify-between gap-3 px-4 py-2.5 text-left"
        aria-expanded={expanded}
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex flex-col gap-0.5">
          <span className="text-[10px] uppercase tracking-[0.1em] font-semibold" style={{ color: "var(--accent-strong)" }}>
            Cost &amp; Impact Estimate
          </span>
          <span className={`font-mono-tab font-semibold leading-tight ${expanded ? "text-[22px]" : "text-[15px]"}`}>
            {fmtUsd(ci.savings_usd_low)}&ndash;{fmtUsd(ci.savings_usd_high)}
          </span>
        </div>
        <svg
          width="12"
          height="12"
          viewBox="0 0 16 16"
          fill="none"
          aria-hidden
          className="shrink-0 text-[var(--muted)] transition-transform"
          style={{ transform: expanded ? "rotate(180deg)" : undefined }}
        >
          <path d="M3 6l5 5 5-5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {expanded && (
        <div className="px-4 pb-4">
          <div className="text-[11.5px] text-[var(--muted)] mb-3">
            Potential avoided cost on one flagged pair &mdash;{" "}
            <span className="font-mono-tab">
              {ci.savings_pct_low != null ? Math.round(ci.savings_pct_low * 100) : "?"}&ndash;
              {ci.savings_pct_high != null ? Math.round(ci.savings_pct_high * 100) : "?"}%
            </span>{" "}
            of DESC&apos;s project cost
          </div>
          <div className="flex flex-col gap-1.5 text-[12px] leading-snug">
            <div className="flex gap-1.5">
              <span
                className="shrink-0 font-mono-tab text-[10px] font-semibold px-1.5 rounded leading-[18px]"
                style={{ background: "color-mix(in srgb, var(--desc-color) 15%, transparent)", color: "var(--desc-color)" }}
              >
                DESC
              </span>
              <span>
                {ci.desc_project_title} &mdash; <span className="font-mono-tab">{fmtUsd(ci.desc_total_cost_usd)}</span>{" "}
                <span className="text-[var(--muted)]">(public filing)</span>
              </span>
            </div>
            <div className="flex gap-1.5">
              <span
                className="shrink-0 font-mono-tab text-[10px] font-semibold px-1.5 rounded leading-[18px]"
                style={{ background: "color-mix(in srgb, var(--gpc-color) 15%, transparent)", color: "var(--gpc-color)" }}
              >
                GPC
              </span>
              <span>
                {ci.gpc_project_titles.join(" & ")} &mdash; <span className="text-[var(--muted)]">cost redacted (CEII)</span>
              </span>
            </div>
          </div>
          <div className="text-[11px] text-[var(--muted)] leading-relaxed mt-3 pt-3 border-t border-[var(--border)]">
            Same facility (<span className="font-mono-tab">{ci.distance_mi} mi</span> apart), but scheduled{" "}
            <span className="font-mono-tab">{ci.day_gap}</span> days (<span className="font-mono-tab">{yrs}</span> yrs) apart
            under the status quo.
            <details className="mt-2" open={open} onToggle={(e) => setOpen(e.currentTarget.open)}>
              <summary className="cursor-pointer hover:text-[var(--foreground)] transition-colors">Methodology &amp; sources</summary>
              <p className="mt-1.5">{ci.benchmark_source}</p>
              <p className="mt-1.5">{ci.gpc_cost_note}</p>
            </details>
          </div>
        </div>
      )}
    </div>
  );
}
