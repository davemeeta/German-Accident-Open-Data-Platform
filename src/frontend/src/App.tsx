import { useState } from "react";
import type { Filters } from "./lib/api";
import { FilterBar } from "./components/FilterBar";
import { Headline } from "./components/Headline";
import { HotspotMap } from "./components/HotspotMap";
import { ChoroplethMap } from "./components/ChoroplethMap";
import { RankingChart } from "./components/RankingChart";
import { TrendChart } from "./components/TrendChart";
import { ProvenanceFooter } from "./components/ProvenanceFooter";

export default function App() {
  const [filters, setFilters] = useState<Filters>({ state: "", year: 2023, category: "" });
  return (
    <div className="min-h-full">
      <header className="max-w-6xl mx-auto px-6 pt-8 pb-4">
        <h1 className="font-display text-2xl font-bold text-text">
          Unfallatlas <span className="text-brand">Risk Lens</span>
        </h1>
        <p className="text-sm text-muted mt-1">
          German road-accident open data, 2016 - 2024, joined on the official AGS key.
        </p>
      </header>
      <FilterBar filters={filters} onChange={setFilters} />
      <main className="max-w-6xl mx-auto px-6 py-6 space-y-6">
        <div className="grid lg:grid-cols-3 gap-6">
          <Headline filters={filters} />
          <div className="lg:col-span-2"><HotspotMap filters={filters} /></div>
        </div>
        <div className="grid lg:grid-cols-2 gap-6">
          <ChoroplethMap filters={filters} />
          <RankingChart filters={filters} />
        </div>
        <TrendChart filters={filters} />
      </main>
      <ProvenanceFooter />
    </div>
  );
}
