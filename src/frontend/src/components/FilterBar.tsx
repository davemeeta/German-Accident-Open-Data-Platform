import type { Filters } from "../lib/api";
import { STATES } from "../lib/format";

const YEARS = [2024,2023,2022,2021,2020,2019,2018,2017,2016];
const SEVS: { value: Filters["category"]; label: string }[] = [
  { value: "", label: "All severities" },
  { value: "1", label: "Fatal" },
  { value: "2", label: "Serious" },
  { value: "3", label: "Light" },
];
const cls = "bg-ink border border-line rounded-lg px-3 py-2 text-sm text-text focus:border-brand focus:outline-none";

export function FilterBar({ filters, onChange }: { filters: Filters; onChange: (f: Filters) => void }) {
  return (
    <div className="sticky top-0 z-[1000] bg-ink/90 backdrop-blur border-b border-line">
      <div className="max-w-6xl mx-auto px-6 py-3 flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1 text-xs text-muted">Region
          <select className={cls} value={filters.state} onChange={(e) => onChange({ ...filters, state: e.target.value })}>
            {STATES.map((s) => <option key={s.code} value={s.code}>{s.name}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-muted">Year
          <select className={cls} value={filters.year} onChange={(e) => onChange({ ...filters, year: +e.target.value })}>
            {YEARS.map((y) => <option key={y} value={y}>{y}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-muted">Severity
          <select className={cls} value={filters.category}
            onChange={(e) => onChange({ ...filters, category: e.target.value as Filters["category"] })}>
            {SEVS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </label>
      </div>
    </div>
  );
}
