import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { AgentInfo, FrameworkInfo } from "../types";

export default function AgentStudio() {
  const [agents, setAgents] = useState<AgentInfo[] | null>(null);
  const [frameworks, setFrameworks] = useState<FrameworkInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.listAgents(), api.listFrameworks()])
      .then(([a, f]) => {
        setAgents(a);
        setFrameworks(f);
      })
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold">Agent Studio</h1>
      <p className="mb-6 max-w-2xl text-sm text-ink-500">
        The same four agents below can be orchestrated by either framework (Phase 6) — pick one on the Plan a
        Trip form. Only the sequencing engine changes; the agents&apos; own prompts, JSON contracts, and (for the
        itinerary step) real geocoding logic stay identical either way.
      </p>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-500">Orchestration Frameworks</h2>
      {!frameworks && !error && <p className="mb-6 text-sm text-ink-500">Loading…</p>}
      {frameworks && (
        <div className="mb-8 grid gap-3 sm:grid-cols-2">
          {frameworks.map((f) => (
            <div key={f.id} className="rounded-xl2 border border-ink-900/5 bg-white p-4">
              <div className="mb-1 flex items-center gap-2">
                <span className="font-semibold text-ink-900">{f.label}</span>
                {f.available ? (
                  <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
                    Available
                  </span>
                ) : (
                  <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-700">
                    Not installed
                  </span>
                )}
              </div>
              <p className="text-sm text-ink-500">{f.description}</p>
            </div>
          ))}
        </div>
      )}

      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-500">Agent Roster</h2>
      {!agents && !error && <p className="text-sm text-ink-500">Loading…</p>}
      {agents && (
        <div className="overflow-hidden rounded-xl2 border border-ink-900/5 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-ink-900/5 text-xs uppercase tracking-wide text-ink-500">
              <tr>
                <th className="px-4 py-3">Agent</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Goal</th>
                <th className="px-4 py-3">Data source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-900/5">
              {agents.map((a) => (
                <tr key={a.id}>
                  <td className="px-4 py-3 font-medium text-ink-900">{a.name}</td>
                  <td className="px-4 py-3">{a.role}</td>
                  <td className="px-4 py-3 text-ink-500">{a.goal}</td>
                  <td className="px-4 py-3 text-ink-500">{a.data_source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
