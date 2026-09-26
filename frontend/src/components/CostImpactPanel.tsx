"use client";

import { useState } from "react";
import type { CostImpact } from "@/lib/types";

function fmtUsd(n: number | null) {
  if (n == null) return "n/a";
  return "$" + Math.round(n).toLocaleString("en-US");
}

export default function CostImpactPanel({ ci }: { ci: CostImpact }) {
  const [open, setOpen] = useState(false);
  const yrs = ci.day_gap != null ? (ci.day_gap / 365.25).toFixed(1) : null;

  return (
    <div className="m-3 mx-4 border border-[#3a4a2e] rounded-xl p-3.5 px-4 bg-gradient-to-b from-[#1a2416] to-[#141c11]">
      <div className="text-[10.5px] uppercase tracking-wide text-lime-500 font-bold mb-1.5">
        Bonus &middot; Cost &amp; Impact Estimate
      </div>
      <div className="text-xl font-bold mb-0.5">
        {fmtUsd(ci.savings_usd_low)}&ndash;{fmtUsd(ci.savings_usd_high)}
      </div>
      <div className="text-[11.5px] text-[var(--muted)] mb-2.5">
        potential avoided cost, one flagged pair &middot;{" "}
        {ci.savings_pct_low != null ? Math.round(ci.savings_pct_low * 100) : "?"}&ndash;
        {ci.savings_pct_high != null ? Math.round(ci.savings_pct_high * 100) : "?"}% of DESC&apos;s own project cost
      </div>
      <div className="text-xs leading-relaxed my-1">
        <b className="text-blue-500">DESC</b> {ci.desc_project_title} &mdash; {fmtUsd(ci.desc_total_cost_usd)} (public filing)
      </div>
      <div className="text-xs leading-relaxed my-1">
        <b className="text-orange-500">GPC</b> {ci.gpc_project_titles.join(" & ")} &mdash; cost redacted as CEII
      </div>
      <div className="text-[10.8px] text-[var(--muted)] leading-relaxed mt-2 pt-2 border-t border-[var(--border)]">
        Same facility ({ci.distance_mi} mi apart), but scheduled {ci.day_gap} days ({yrs} yrs) apart under the status quo.
        <details className="mt-1.5" open={open} onToggle={(e) => setOpen(e.currentTarget.open)}>
          <summary className="cursor-pointer text-[var(--muted)]">Methodology &amp; sources</summary>
          <p className="mt-1.5">{ci.benchmark_source}</p>
          <p className="mt-1.5">{ci.gpc_cost_note}</p>
        </details>
      </div>
    </div>
  );
}
