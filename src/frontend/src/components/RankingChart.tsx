import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { api, type Filters } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { SEV_COLOR, fmt } from "../lib/format";
import { Panel } from "./Panel";

const C: Record<string, string> = { "": SEV_COLOR.all, "1": SEV_COLOR.fatal, "2": SEV_COLOR.serious, "3": SEV_COLOR.light };

export function RankingChart({ filters }: { filters: Filters }) {
  const { data, error, loading } = useAsync(
    () => api.byRegion(filters, "district", 10),
    [filters.state, filters.year, filters.category],
  );
  const rows = (data ?? []).map((r) => ({ name: r.name ?? r.ags, value: r.accident_count }));
  const color = C[filters.category];
  return (
    <Panel title="Top districts" subtitle="by accident count" loading={loading} error={error}>
      {rows.length > 0 ? (
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 40 }}>
            <XAxis type="number" tick={{ fill: "#8896ad", fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="name" width={120}
              tick={{ fill: "#e8eef7", fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }}
              contentStyle={{ background: "#0a0f1c", border: "1px solid #243049", borderRadius: 8, color: "#e8eef7" }}
              formatter={(v) => [fmt(Number(v)), "accidents"]} />
            <Bar dataKey="value" radius={[0, 4, 4, 0]}>
              {rows.map((_, i) => <Cell key={i} fill={color} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : !loading && !error ? (
        <p className="text-muted text-sm">No district data.</p>
      ) : null}
    </Panel>
  );
}
