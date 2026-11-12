import { FormEvent, useState } from "react";
import Spinner from "./Spinner";
import { api, ApiError } from "../api/client";

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
}

const SUGGESTED_QUESTIONS = [
  "What's my cheapest flight option?",
  "How is my budget allocated?",
  "What's the best way to get from the airport?",
];

export default function TripAssistant({ tripId }: { tripId: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ask(question: string) {
    const text = question.trim();
    if (!text || loading) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setLoading(true);
    setError(null);
    try {
      const { answer } = await api.askTripAssistant(tripId, text);
      setMessages((m) => [...m, { role: "assistant", text: answer }]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    ask(input);
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="rounded-xl2 border border-brand-100 bg-brand-50/50 p-4 text-xs text-ink-600">
        Answers are grounded only in this trip's real computed data (budget allocation, flight/transport
        recommendations, itinerary) — never a fabricated price, time, or availability.
      </div>

      {messages.length === 0 && (
        <div className="flex flex-wrap gap-2">
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => ask(q)}
              className="rounded-full border border-ink-900/10 bg-white px-3 py-1.5 text-xs font-medium text-ink-700 hover:bg-brand-50"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      <div className="flex flex-col gap-3">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`max-w-[85%] rounded-xl2 p-3 text-sm ${
              m.role === "user"
                ? "ml-auto bg-brand-600 text-white"
                : "border border-ink-900/5 bg-white shadow-card text-ink-900"
            }`}
          >
            {m.text}
          </div>
        ))}
        {loading && (
          <div className="max-w-[85%] rounded-xl2 border border-ink-900/5 bg-white shadow-card p-3">
            <Spinner />
          </div>
        )}
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      <form onSubmit={handleSubmit} className="flex items-end gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about this trip's budget, flights, or transport…"
          className="flex-1 rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-transform hover:-translate-y-0.5 hover:bg-brand-700 active:translate-y-0 disabled:opacity-50"
        >
          Ask
        </button>
      </form>
    </div>
  );
}
