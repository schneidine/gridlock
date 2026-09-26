"use client";

import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import { useEffect } from "react";
import type { Overlap, Project } from "@/lib/types";

// Leaflet renders these as raw SVG presentation attributes, not through the
// CSS cascade, so we use literal hex values here rather than var(--x) --
// custom-property resolution inside SVG presentation attributes is
// inconsistent across browsers.
const DESC_COLOR = "#2563eb";
const GPC_COLOR = "#ea580c";

function fmtDate(iso: string | null) {
  if (!iso) return "date n/a";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "date n/a";
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short" });
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

export default function GridlockMap({
  projects,
  selectedOverlap,
}: {
  projects: Project[];
  selectedOverlap: { a: Project; b: Project } | null;
}) {
  const pair: [[number, number], [number, number]] | null = selectedOverlap
    ? [selectedOverlap.a.geo_center as [number, number], selectedOverlap.b.geo_center as [number, number]]
    : null;

  return (
    <MapContainer
      center={[32.9, -81.3]}
      zoom={8}
      className="h-full w-full"
      style={{ background: "#e5e3df" }}
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; OpenStreetMap contributors &copy; CARTO'
        subdomains="abcd"
        maxZoom={19}
      />
      {projects.map((p) => {
        if (!p.geo_center) return null;
        const color = p.utility.startsWith("Dominion") ? DESC_COLOR : GPC_COLOR;
        const dashed = p.geo_confidence !== "confirmed";
        return (
          <div key={p.project_id}>
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
                <b>{p.title}</b>
                <br />
                {p.utility}
                <br />
                In-service: {fmtDate(p.in_service_date)}
                <br />
                <span className="text-xs">{p.geo_confidence?.replace("_", " ")}</span>
              </Popup>
            </CircleMarker>
            {p.geo_points && p.geo_points.length === 2 && (
              <Polyline
                positions={p.geo_points}
                pathOptions={{ color, weight: 2, opacity: dashed ? 0.35 : 0.7 }}
              />
            )}
          </div>
        );
      })}
      {pair && (
        <Polyline positions={pair} pathOptions={{ color: "#ffffff", weight: 2, dashArray: "5,5", opacity: 0.8 }} />
      )}
      <FocusController pair={pair} />
    </MapContainer>
  );
}
