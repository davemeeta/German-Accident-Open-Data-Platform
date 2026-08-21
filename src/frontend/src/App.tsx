import { useState } from "react";
import type { Filters } from "./lib/api";
import { FilterBar } from "./components/FilterBar";
import { Headline } from "./components/Headline";
import { HotspotMap } from "./components/HotspotMap";
import { ChoroplethMap } from "./components/ChoroplethMap";
import { RankingChart } from "./components/RankingChart";
import { TrendChart } from "./components/TrendChart";
import { AgentChat } from "./components/AgentChat";
import { ProvenanceFooter } from "./components/ProvenanceFooter";

export default function App() {
  const [filters, setFilters] = useState<Filters>({ state: "", year: 2023, category: "" });
  return (
    <div className="min-h-full">
      <header className="max-w-6xl mx-auto px-6 pt-8 pb-4 flex items-center gap-5">
      {/* Traffic light — severity colors as brand identity */}
      <div className="flex flex-col items-center gap-1.5 bg-[#1a2230] border border-[#243049] rounded-xl px-2.5 py-3 shrink-0">
      <div className="w-5 h-5 rounded-full bg-[#ef4444] shadow-[0_0_8px_2px_rgba(239,68,68,0.5)]" />
      <div className="w-5 h-5 rounded-full bg-[#f59e0b] shadow-[0_0_8px_2px_rgba(245,158,11,0.4)]" />
      <div className="w-5 h-5 rounded-full bg-[#319255] shadow-[0_0_8px_2px_rgba(34,197,94,0.5)]" />   
    </div>
    <div>
    <h1 className="font-display text-2xl font-bold text-text">
      Unfallatlas <span className="text-brand">Risk Lens</span>
    </h1>
    <p className="text-sm text-muted mt-1">
      German road-accident open data, 2016–2024, joined on the official AGS key.
    </p>
    <div className="flex gap-4 mt-2 text-xs text-muted">
      <span><span className="text-[#ef4444] font-bold">●</span> Fatal</span>
      <span><span className="text-[#f59e0b] font-bold">●</span> Serious</span>
      <span><span className="text-[#319255] font-bold">●</span> Light injury</span>
    </div>
  </div>
</header>
      <div className="max-w-6xl mx-auto px-6 pb-6">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-brand text-base leading-none">✦</span>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-muted">Ask Atlas</h2>
        </div>
        <AgentChat />
      </div>

      <div className="max-w-6xl mx-auto px-6 flex items-center gap-4 pb-3">
        <div className="h-px flex-1 bg-line" />
        <span className="text-xs font-semibold uppercase tracking-widest text-muted whitespace-nowrap">
          Or Explore The Dashboard Yourself
        </span>
        <div className="h-px flex-1 bg-line" />
      </div>

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
