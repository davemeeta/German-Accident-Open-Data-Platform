const AGENT_BASE = (import.meta.env.VITE_AGENT_API_BASE as string | undefined) ?? "http://127.0.0.1:8001";

export interface AskResponse {
  narration: string;
  trace_path: string;
  backend: string;
  grounding_gate_triggered: boolean;
  session_id: string;
}

export async function askAgent(question: string, sessionId: string | null): Promise<AskResponse> {
  const res = await fetch(`${AGENT_BASE}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId }),
  });
  if (!res.ok) {
    const b = await res.json().catch(() => ({}));
    throw new Error((b as { detail?: string }).detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<AskResponse>;
}
