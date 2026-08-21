import { useRef, useState } from "react";
import { askAgent } from "../lib/agentApi";

interface Message {
  role: "user" | "assistant" | "error";
  text: string;
  groundingGateTriggered?: boolean;
}

function formatBackend(backend: string): string {
  // "ollama:llama3.2:3b" -> "Ollama · llama3.2:3b", "groq:openai/gpt-oss-120b" -> "Groq · openai/gpt-oss-120b"
  const sep = backend.indexOf(":");
  if (sep === -1) return backend;
  const provider = backend.slice(0, sep);
  const model = backend.slice(sep + 1);
  return `${provider.charAt(0).toUpperCase()}${provider.slice(1)} · ${model}`;
}

export function AgentChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [lastBackend, setLastBackend] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  async function send() {
    const question = input.trim();
    if (!question || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: question }]);
    setLoading(true);
    try {
      const res = await askAgent(question, sessionId);
      setSessionId(res.session_id);
      setLastBackend(res.backend);
      setMessages((m) => [
        ...m,
        { role: "assistant", text: res.narration, groundingGateTriggered: res.grounding_gate_triggered },
      ]);
    } catch (e) {
      setMessages((m) => [...m, { role: "error", text: (e as Error).message }]);
    } finally {
      setLoading(false);
      requestAnimationFrame(() => listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" }));
    }
  }

  function newConversation() {
    setMessages([]);
    setSessionId(null);
  }

  return (
    <section className="bg-surface border border-line rounded-2xl p-6 flex flex-col">
      <header className="mb-4 flex items-baseline justify-between gap-3">
        <div>
          <h2 className="font-display text-lg font-bold text-text">
            Atlas <span className="text-brand">●</span>
          </h2>
          <p className="text-xs text-muted mt-1">Your road-safety data assistant</p>
        </div>
        {messages.length > 0 && (
          <button
            onClick={newConversation}
            className="text-xs text-muted hover:text-brand transition-colors shrink-0"
          >
            New conversation
          </button>
        )}
      </header>

      <div ref={listRef} className="flex-1 min-h-[220px] max-h-[420px] overflow-y-auto space-y-3 mb-4 pr-1">
        {messages.length === 0 && (
          <div className="max-w-[85%] rounded-xl px-4 py-3 text-sm bg-ink text-text border border-line">
            Hi, I'm Atlas 👋 What brings you here today? Ask me anything about German road accidents —
            like <span className="text-muted italic">"How many accidents were there in Bavaria in 2022?"</span>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-xl px-4 py-2.5 text-sm whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-brand/15 text-text border border-brand/30"
                  : m.role === "error"
                  ? "bg-fatal/10 text-fatal border border-fatal/30"
                  : "bg-ink text-text border border-line"
              }`}
            >
              {m.text}
              {m.groundingGateTriggered && (
                <div className="mt-2 pt-2 border-t border-line/60 text-xs text-muted flex items-center gap-1.5">
                  <span className="text-brand">●</span>
                  Grounding check caught and corrected an unverified number before showing this answer
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-ink text-muted border border-line rounded-xl px-4 py-2.5 text-sm animate-pulse">
              Checking the data…
            </div>
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => { e.preventDefault(); send(); }}
        className="flex gap-2"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about the data…"
          disabled={loading}
          className="flex-1 bg-ink border border-line rounded-lg px-3 py-2 text-sm text-text placeholder:text-muted focus:outline-none focus:border-brand disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="bg-brand text-ink font-semibold text-sm px-4 py-2 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90 transition-opacity shrink-0"
        >
          Ask
        </button>
      </form>

      {lastBackend && (
        <p className="text-[11px] text-muted/70 mt-3 text-right">
          Powered by {formatBackend(lastBackend)}
        </p>
      )}
    </section>
  );
}
