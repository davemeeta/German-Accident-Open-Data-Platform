import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceDot } from "recharts";
import { api, type Filters } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { SEV_COLOR, fmt } from "../lib/format";
import { Panel } from "./Panel";

export function TrendChart({ filters }: { filters: Filters }) {
  const { data, error, loading } = useAsync(
    () => api.trend(filters),
    [filters.state, filters.category],
  );
  const series = data?.series ?? [];
  const cur = series.find((p) => p.year === filters.year);
  return (
    <Panel title="Trend" subtitle="accidents per year" loading={loading} error={error}>
      {series.length > 0 ? (
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={series} margin={{ left: 8, right: 16, top: 8 }}>
            <XAxis dataKey="year" tick={{ fill: "#8896ad", fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#8896ad", fontSize: 11 }} axisLine={false} tickLine={false} width={48}
              tickFormatter={(v: number) => (v >= 1000 ? `${Math.round(v / 1000)}k` : String(v))} />
            <Tooltip contentStyle={{ background: "#0a0f1c", border: "1px solid #243049", borderRadius: 8, color: "#e8eef7" }}
              formatter={(v) => [fmt(Number(v)), "accidents"]} />
            <Line type="monotone" dataKey="accident_count" stroke={SEV_COLOR.all} strokeWidth={2} dot={{ r: 3 }} />
            {cur && <ReferenceDot x={cur.year} y={cur.accident_count} r={5} fill={SEV_COLOR.serious} stroke="none" />}
          </LineChart>
        </ResponsiveContainer>
      ) : null}
    </Panel>
  );
}
