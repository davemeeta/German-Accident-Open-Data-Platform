import L from "leaflet";
import { api, type Filters } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { SEV_COLOR } from "../lib/format";
import { Panel } from "./Panel";
import { LeafletMap } from "./LeafletMap";

export function HotspotMap({ filters }: { filters: Filters }) {
  const { data, error, loading } = useAsync(
    () => api.hotspots(filters),
    [filters.state, filters.year, filters.category],
  );
  const hotspots = data?.hotspots ?? [];
  const mapKey = `hot-${filters.state}-${filters.year}-${filters.category}`;

  function onMap(m: L.Map) {
    if (!hotspots.length) return;
    const lg = L.layerGroup().addTo(m);
    const pts: L.LatLngExpression[] = [];
    for (const h of hotspots) {
      const sev = h.severity_score / Math.max(h.total, 1);
      const color = sev >= 4 ? SEV_COLOR.fatal : sev >= 2 ? SEV_COLOR.serious : SEV_COLOR.light;
      L.circleMarker([h.lat, h.lon], { radius: Math.min(4 + h.total, 22), color, fillOpacity: 0.55, weight: 1 })
        .bindPopup(`<b>${h.district ?? h.district_ags}</b><br>${h.total} crashes: ${h.fatal}F ${h.serious}S ${h.light}L`)
        .addTo(lg);
      pts.push([h.lat, h.lon]);
    }
    if (pts.length) m.fitBounds(pts as L.LatLngBoundsExpression, { padding: [24, 24] });
  }

  return (
    <Panel title="Hotspots" subtitle={`${hotspots.length} clusters`} loading={loading} error={error}>
      {hotspots.length > 0 ? (
        <LeafletMap key={mapKey} onMap={onMap} tiles />
      ) : !loading && !error ? (
        <div className="h-[420px] rounded-lg bg-ink flex items-center justify-center text-muted text-sm">
          No hotspot clusters for this filter. Try "All severities".
        </div>
      ) : null}
    </Panel>
  );
}
