import L from "leaflet";
import { api, type Filters } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { Panel } from "./Panel";
import { LeafletMap } from "./LeafletMap";

const SCALE = ["#cfe3fd", "#86bdfb", "#4f9cf9", "#2d6fb3", "#1e3a5f"];

function quantileBreaks(values: number[]): number[] {
  const v = values.filter((x) => x != null).sort((a, b) => a - b);
  if (!v.length) return [0, 0, 0, 0, 0];
  return [0, 0.2, 0.4, 0.6, 0.8].map((q) => Math.round(v[Math.floor(q * (v.length - 1))]));
}

export function ChoroplethMap({ filters }: { filters: Filters }) {
  const { data, error, loading } = useAsync(
    () => api.choropleth(filters),
    [filters.state, filters.year, filters.category],
  );
  const features = data?.features ?? [];
  const mapKey = `choro-${filters.state}-${filters.year}-${filters.category}`;

  function onMap(m: L.Map) {
    if (!features.length || !data) return;
    const vals = features.map((f) => f.properties.value).filter((x): x is number => x != null);
    const bk = quantileBreaks(vals);
    const colorOf = (v: number | null) => {
      if (v == null) return "#243049";
      for (let i = bk.length - 1; i >= 0; i--) if (v >= bk[i]) return SCALE[i];
      return SCALE[0];
    };
    const gj = L.geoJSON(data as unknown as GeoJSON.GeoJsonObject, {
      style: (feat) => ({
        fillColor: colorOf((feat?.properties as { value: number | null }).value),
        weight: 0.4, color: "#0a0f1c", fillOpacity: 0.85,
      }),
      onEachFeature: (feat, lyr) => {
        const p = feat.properties as { name: string | null; ags: string; value: number | null };
        lyr.bindPopup(`<b>${p.name ?? p.ags}</b><br>${data.value_label}: ${p.value ?? "n/a"}`);
      },
    }).addTo(m);
    if (gj.getBounds().isValid()) m.fitBounds(gj.getBounds(), { padding: [20, 20] });
  }

  return (
    <Panel title="District choropleth" subtitle={`${filters.year}`} loading={loading} error={error}>
      {features.length > 0 ? (
        <LeafletMap key={mapKey} onMap={onMap} />
      ) : !loading && !error ? (
        <div className="h-[420px] rounded-lg bg-ink flex items-center justify-center text-muted text-sm">
          No geometry data for this selection.
        </div>
      ) : null}
    </Panel>
  );
}
