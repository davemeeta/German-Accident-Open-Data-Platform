import type { ReactNode } from "react";
export function Panel({ title, subtitle, loading, error, children, className = "" }: {
  title: string; subtitle?: string; loading?: boolean; error?: string | null;
  children: ReactNode; className?: string;
}) {
  return (
    <section className={`bg-surface border border-line rounded-2xl p-5 flex flex-col ${className}`}>
      <header className="mb-4 flex items-baseline justify-between gap-3">
        <h2 className="font-display text-sm font-semibold tracking-wide uppercase text-text">{title}</h2>
        {subtitle && <span className="text-xs text-muted">{subtitle}</span>}
      </header>
      {error ? <p className="text-red-400 text-sm">Error: {error}</p>
       : loading ? <p className="text-muted text-sm animate-pulse">Loading...</p>
       : children}
    </section>
  );
}
