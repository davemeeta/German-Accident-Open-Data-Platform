import { useAsync } from "../lib/useAsync";
import type { Provenance } from "../lib/types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://127.0.0.1:8000";

export function ProvenanceFooter() {
  const { data } = useAsync(
    () => fetch(`${BASE}/metadata/sources`).then((r) => r.json() as Promise<Provenance[]>), [],
  );
  return (
    <footer className="border-t border-line mt-8">
      <div className="max-w-6xl mx-auto px-6 py-6 text-xs text-muted">
        <p className="mb-2 uppercase tracking-widest">Data sources</p>
        <ul className="flex flex-wrap gap-x-6 gap-y-1">
          {(data ?? []).map((s, i) => (
            <li key={i}>{s.source} — {s.license_url
              ? <a href={s.license_url} target="_blank" rel="noreferrer" className="text-brand hover:underline">{s.license}</a>
              : s.license}
            </li>
          ))}
        </ul>
      </div>
    </footer>
  );
}
