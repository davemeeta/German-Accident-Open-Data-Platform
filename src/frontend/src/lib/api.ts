import type { CountResponse, RegionCount, HotspotResponse, TrendResponse, ChoroplethResponse } from "./types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://127.0.0.1:8000";

async function get<T>(path: string): Promise<T> {
  const url = `${BASE}${path}`;
  const res = await fetch(url);
  if (!res.ok) {
    const b = await res.json().catch(() => ({}));
    throw new Error((b as { detail?: string }).detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export interface Filters { state: string; year: number; category: "" | "1" | "2" | "3"; }

function qs(f: Filters, extra: Record<string, string | number> = {}): string {
  const p = new URLSearchParams();
  if (f.state) p.set("state", f.state);
  p.set("year", String(f.year));
  if (f.category) p.set("category", f.category);
  for (const [k, v] of Object.entries(extra)) p.set(k, String(v));
  return p.toString();
}

export const api = {
  count:      (f: Filters) => get<CountResponse>(`/aggregates/accidents?${qs(f)}`),
  byRegion:   (f: Filters, level = "district", limit = 10) =>
                get<RegionCount[]>(`/aggregates/accidents/by-region?${qs(f, { level, limit, order: "desc" })}`),
hotspots: (f: Filters, limit = 150) => {
    const isFatal = f.category === "1";
    return get<HotspotResponse>(`/aggregates/hotspots?${qs(f, {
      limit,
      min_count: isFatal ? 1 : 3,
      precision: isFatal ? 2 : 3,
    })}`);
  },
  trend:      (f: Filters) => {
                const p = new URLSearchParams();
                if (f.state) p.set("state", f.state);
                if (f.category) p.set("category", f.category);
                return get<TrendResponse>(`/stats/trend?${p}`);
              },
  choropleth: (f: Filters) =>
                get<ChoroplethResponse>(`/regions/choropleth?${qs(f, { metric: "count" })}`),
};
