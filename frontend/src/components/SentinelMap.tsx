"use client";

import L from "leaflet";
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import { Fragment, useEffect, useLayoutEffect, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import type { Project } from "@/lib/types";
import { UTILITIES, utilityStyle } from "@/lib/utilities";
import { setTheme, storedTheme, useTheme } from "@/lib/theme";

// Leaflet renders these as raw SVG presentation attributes, not through the
// CSS cascade, so we use literal hex values here rather than var(--x) --
// custom-property resolution inside SVG presentation attributes is
// inconsistent across browsers.
const SELECTED_COLOR = "#eb9256";
// Overlap ring: yellow reads on the dark basemap, a darker amber on the light one.
const FLAG_COLOR = { dark: "#facc15", light: "#b45309" };

// The pipeline notes "1 of 2 endpoints located; center uses the located one(s) only" when a
// project's position rests on only some of its stations.
function partialNote(p: Project) {
  const m = p.geo_notes?.map((n) => n.match(/(\d+) of (\d+) endpoints located/)).find(Boolean);
  return m ? `${m[1]} of ${m[2]} stations located; position is approximate` : null;
}

function fmtDate(iso: string | null) {
  if (!iso) return "date n/a";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "date n/a";
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short" });
}

/** Sun/moon button stacked under Leaflet's zoom +/- in the top-left corner. */
function ThemeToggleControl() {
  const map = useMap();
  const theme = useTheme();
  const [host] = useState(() => L.DomUtil.create("div", "leaflet-control leaflet-bar"));

  // React's dev-mode remount resets <html>'s attributes, clearing the one the
  // layout's inline script set; put it back before paint. No-op in production.
  useLayoutEffect(() => {
    document.documentElement.setAttribute("data-theme", storedTheme());
  }, []);

  useEffect(() => {
    const corner = map.getContainer().querySelector(".leaflet-top.leaflet-left");
    if (!corner) return;
    corner.appendChild(host);
    L.DomEvent.disableClickPropagation(host); // clicks shouldn't pan or zoom the map
    return () => host.remove();
  }, [map, host]);

  const next = theme === "dark" ? "light" : "dark";
  return createPortal(
    <a
      href="#"
      role="button"
      className="gl-theme-toggle"
      title={`Switch to ${next} mode`}
      aria-label={`Switch to ${next} mode`}
      onClick={(e) => {
        e.preventDefault();
        setTheme(next);
      }}
    >
      {theme === "dark" ? <SunIcon /> : <MoonIcon />}
    </a>,
    host
  );
}

function SunIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z" />
    </svg>
  );
}

/** Recenters/zooms the map to fit two points whenever the selected overlap changes. */
function FocusController({ pair }: { pair: [[number, number], [number, number]] | null }) {
  const map = useMap();
  useEffect(() => {
    if (!pair) return;
    map.fitBounds(pair, { padding: [80, 80], maxZoom: 11 });
  }, [pair, map]);
  return null;
}

export default function SentinelMap({
  projects,
  flagCountByProject,
  selectedOverlap,
}: {
  projects: Project[];
  flagCountByProject: Record<string, number>;
  selectedOverlap: { a: Project; b: Project } | null;
}) {
  const flagColor = FLAG_COLOR[useTheme()];
  const pair: [[number, number], [number, number]] | null = selectedOverlap
    ? [selectedOverlap.a.geo_center as [number, number], selectedOverlap.b.geo_center as [number, number]]
    : null;

  return (
    <div className="relative h-full w-full">
      <MapContainer
        center={[32.9, -81.3]}
        zoom={8}
        className="h-full w-full"
        style={{ background: "var(--background)" }}
      >
        <TileLayer
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          maxZoom={19}
          className="gl-dark-tiles"
        />
        {projects.map((p) => {
          if (!p.geo_center) return null;
          const color = utilityStyle(p.utility).color;
          const dashed = p.geo_confidence !== "confirmed";
          const flagCount = flagCountByProject[p.project_id] ?? 0;
          return (
            <Fragment key={p.project_id}>
              {flagCount > 0 && (
                <CircleMarker
                  center={p.geo_center}
                  radius={10}
                  interactive={false}
                  pathOptions={{ color: flagColor, weight: 2, opacity: 0.9, fill: false }}
                />
              )}
              <CircleMarker
                center={p.geo_center}
                radius={5}
                pathOptions={{
                  color,
                  weight: dashed ? 1 : 2,
                  fillColor: color,
                  fillOpacity: dashed ? 0.35 : 0.85,
                  dashArray: dashed ? "2,2" : undefined,
                }}
              >
                <Popup>
                  <div className="gl-popup-title">{p.title}</div>
                  <div className="gl-popup-meta">{p.utility}</div>
                  <div className="gl-popup-meta">
                    In-service: {p.in_service_date ? fmtDate(p.in_service_date) : (p.in_service_year ?? "date n/a")}
                  </div>
                  {flagCount > 0 && (
                    <div className="gl-popup-flag">
                      Flagged in {flagCount} overlap{flagCount === 1 ? "" : "s"}
                    </div>
                  )}
                  <div className="gl-popup-conf">{p.geo_confidence?.replace("_", " ")}</div>
                  {partialNote(p) && <div className="gl-popup-meta">{partialNote(p)}</div>}
                </Popup>
              </CircleMarker>
              {p.geo_points && p.geo_points.length === 2 && (
                <Polyline
                  positions={p.geo_points}
                  pathOptions={{ color, weight: 2, opacity: dashed ? 0.35 : 0.7 }}
                />
              )}
            </Fragment>
          );
        })}
        {pair && (
          <Polyline
            positions={pair}
            pathOptions={{ color: SELECTED_COLOR, weight: 2.5, dashArray: "6,5", opacity: 0.95 }}
          />
        )}
        <FocusController pair={pair} />
        <ThemeToggleControl />
      </MapContainer>
      <MapLegend flagColor={flagColor} />
    </div>
  );
}

function MapLegend({ flagColor }: { flagColor: string }) {
  return (
    <div className="absolute bottom-6 left-3 z-[1000] rounded-lg border border-[var(--border)] bg-[var(--panel)]/90 backdrop-blur-sm px-3 py-2.5 text-[11px] flex flex-col gap-1.5 shadow-lg">
      <div className="text-[9.5px] uppercase tracking-[0.1em] text-[var(--muted)] font-medium">Legend</div>
      {Object.entries(UTILITIES).map(([name, u]) => (
        <LegendRow key={name} swatch={<Dot color={u.color} />} label={`${name} project`} />
      ))}
      <LegendRow swatch={<Dot color="var(--muted)" dashed />} label="Estimated location" />
      <LegendRow
        swatch={<span className="block w-3.5 h-3.5 rounded-full" style={{ border: `2px solid ${flagColor}` }} />}
        label="In a flagged overlap"
      />
      <LegendRow
        swatch={<span className="block w-4 border-t-2 border-dashed" style={{ borderColor: SELECTED_COLOR }} />}
        label="Selected overlap"
      />
    </div>
  );
}

function LegendRow({ swatch, label }: { swatch: ReactNode; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-4 flex justify-center">{swatch}</span>
      <span>{label}</span>
    </div>
  );
}

function Dot({ color, dashed }: { color: string; dashed?: boolean }) {
  return (
    <span
      className="block w-2.5 h-2.5 rounded-full"
      style={
        dashed
          ? { border: `1px dashed ${color}`, background: "transparent" }
          : { background: color, border: `1.5px solid ${color}` }
      }
    />
  );
}
