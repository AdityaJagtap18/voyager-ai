import { useEffect, useState } from "react";
import Spinner from "../components/Spinner";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import type { ModelInfo } from "../types";

export default function ModelsRouting() {
  const [models, setModels] = useState<ModelInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listModels()
      .then(setModels)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <PageHeader
        icon="AI-Engineering/model.svg"
        title="Models & Routing"
        description={
          <>
            The model gateway (Phase 5) routes every agent through one provider-agnostic{" "}
            <code className="rounded bg-ink-900/5 px-1 py-0.5 text-xs">model</code> id, built on LiteLLM.
            &quot;Configured&quot; means the server has the API key that model needs — not that a call
            has actually been test-fired against the provider.
          </>
        }
      />

      {error && <p className="text-sm text-rose-600">{error}</p>}
      {!models && !error && <Spinner />}

      {models && (
        <div className="overflow-hidden rounded-xl2 border border-ink-900/5 bg-white shadow-card">
          <table className="w-full text-left text-sm">
            <thead className="bg-ink-900/5 text-xs uppercase tracking-wide text-ink-500">
              <tr>
                <th className="px-4 py-3">Model</th>
                <th className="px-4 py-3">Provider</th>
                <th className="px-4 py-3">Context window</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-900/5">
              {models.map((m) => (
                <tr key={m.id}>
                  <td className="px-4 py-3">
                    <div className="font-medium text-ink-900">{m.label}</div>
                    <div className="text-xs text-ink-500">{m.id}</div>
                  </td>
                  <td className="px-4 py-3 capitalize">{m.provider}</td>
                  <td className="px-4 py-3">{m.context_window.toLocaleString()} tokens</td>
                  <td className="px-4 py-3">
                    {m.configured ? (
                      <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700">
                        Configured
                      </span>
                    ) : (
                      <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-700">
                        {m.local ? "Local (no server reachability check yet)" : "Needs API key"}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
