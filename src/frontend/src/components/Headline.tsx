import { api, type Filters } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { fmt, SEV_COLOR, STATES } from "../lib/format";

export function Headline({ filters }: { filters: Filters }) {
  const total   = useAsync(() => api.count(filters), [filters.state, filters.year, filters.category]);
  const fatal   = useAsync(() => api.count({ ...filters, category: "1" }), [filters.state, filters.year]);
  const serious = useAsync(() => api.count({ ...filters, category: "2" }), [filters.state, filters.year]);
  const light   = useAsync(() => api.count({ ...filters, category: "3" }), [filters.state, filters.year]);

  const region = STATES.find((s) => s.code === filters.state)?.name ?? "Germany";
  const sev = [fatal.data?.accident_count ?? 0, serious.data?.accident_count ?? 0, light.data?.accident_count ?? 0];
  const mx = Math.max(...sev, 1);
  const bars = [
    { k: "Fatal", v: sev[0], c: SEV_COLOR.fatal },
    { k: "Serious", v: sev[1], c: SEV_COLOR.serious },
    { k: "Light", v: sev[2], c: SEV_COLOR.light },
  ];
  return (
    <section className="bg-surface border border-line rounded-2xl p-6">
      <p className="text-xs uppercase tracking-widest text-muted">Accidents · {region} · {filters.year}{filters.category && " · filtered"}</p>
      <div className="font-display text-6xl font-bold tnum mt-1 mb-5 text-text">
        {total.error ? <span className="text-red-400 text-2xl">{total.error}</span>
          : total.loading ? <span className="text-muted">...</span>
          : fmt(total.data?.accident_count)}
      </div>
      <div className="space-y-2">
        {bars.map((b) => (
          <div key={b.k} className="flex items-center gap-3 text-sm">
            <span className="w-16 text-muted">{b.k}</span>
            <div className="flex-1 h-2 rounded-full bg-ink overflow-hidden">
              <div className="h-full rounded-full" style={{ width: `${(b.v / mx) * 100}%`, background: b.c }} />
            </div>
            <span className="w-20 text-right tnum text-text">{fmt(b.v)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
