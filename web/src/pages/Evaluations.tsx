import { FormEvent, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import PageHeader from "../components/PageHeader";
import type { EvaluationRunDetail, EvaluationRunSummary, FrameworkInfo, ModelInfo } from "../types";

export default function Evaluations() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [frameworks, setFrameworks] = useState<FrameworkInfo[]>([]);
  const [model, setModel] = useState("");
  const [framework, setFramework] = useState("");

  const [runs, setRuns] = useState<EvaluationRunSummary[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [latest, setLatest] = useState<EvaluationRunDetail | null>(null);

  function refreshRuns() {
    api
      .listEvaluationRuns()
      .then(setRuns)
      .catch((e) => setLoadError(e.message));
  }

  useEffect(() => {
    Promise.all([api.listModels(), api.listFrameworks()]).then(([m, f]) => {
      setModels(m);
      setFrameworks(f);
    });
    refreshRuns();
  }, []);

  async function handleRun(e: FormEvent) {
    e.preventDefault();
    setRunning(true);
    setRunError(null);
    try {
      const run = await api.createEvaluationRun({ model: model || undefined, framework: framework || undefined });
      setLatest(run);
      refreshRuns();
    } catch (e) {
      setRunError(e instanceof ApiError ? e.message : "Something went wrong. Is the backend running?");
    } finally {
      setRunning(false);
    }
  }

  async function viewRun(id: string) {
    setRunError(null);
    try {
      setLatest(await api.getEvaluationRun(id));
    } catch (e) {
      setRunError(e instanceof ApiError ? e.message : "Could not load that run.");
    }
  }

  return (
    <div>
      <PageHeader
        icon="AI-Engineering/evaluation.svg"
        title="Evaluations"
        description="A fixed set of canned trip-planning cases (Phase 8), graded automatically on whether planning actually succeeded and produced attractions and an itinerary — catches real breakage (a provider outage, a misconfigured key, a broken agent), not itinerary quality."
      />

      <form onSubmit={handleRun} className="mb-8 flex flex-wrap items-end gap-4 rounded-xl2 border border-ink-900/5 bg-white shadow-card p-6">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Model <span className="font-normal text-ink-500">(optional)</span>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            <option value="">Default</option>
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Framework <span className="font-normal text-ink-500">(optional)</span>
          <select
            value={framework}
            onChange={(e) => setFramework(e.target.value)}
            className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            <option value="">Default (langgraph)</option>
            {frameworks.map((f) => (
              <option key={f.id} value={f.id} disabled={!f.available}>
                {f.label}
                {!f.available ? " (not installed)" : ""}
              </option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          disabled={running}
          className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-transform hover:-translate-y-0.5 hover:bg-brand-700 active:translate-y-0 disabled:opacity-50"
        >
          {running ? "Running…" : "Run eval suite"}
        </button>
        {runError && <p className="text-sm text-rose-600">{runError}</p>}
      </form>

      {latest && (
        <div className="mb-8 rounded-xl2 border border-ink-900/5 bg-white shadow-card p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-500">
              Run {latest.id.slice(0, 8)} · {latest.framework ?? "langgraph"} · {latest.model ?? "default"}
            </h2>
            <span className="text-sm font-medium">
              <span className="text-emerald-600">{latest.pass_count} passed</span>
              {" · "}
              <span className="text-rose-600">{latest.fail_count} failed</span>
            </span>
          </div>
          <div className="flex flex-col gap-2">
            {latest.results.map((r) => (
              <div key={r.case_id} className="rounded-lg border border-ink-900/10 p-3 text-sm">
                <div className="mb-1 flex items-center justify-between">
                  <span className="font-medium text-ink-900">{r.case_id}</span>
                  <span className={r.passed ? "text-emerald-600" : "text-rose-600"}>
                    {r.passed ? "PASS" : "FAIL"} · {r.duration_ms.toFixed(0)} ms
                  </span>
                </div>
                <p className="text-ink-500">{r.description}</p>
                {!r.passed && <p className="mt-1 text-xs text-rose-600">{r.reason}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-500">Run history</h2>
      {loadError && <p className="text-sm text-rose-600">{loadError}</p>}
      {runs.length === 0 && !loadError && <p className="text-sm text-ink-500">No evaluation runs yet.</p>}
      {runs.length > 0 && (
        <div className="overflow-hidden rounded-xl2 border border-ink-900/5 bg-white shadow-card">
          <table className="w-full text-left text-sm">
            <thead className="bg-ink-900/5 text-xs uppercase tracking-wide text-ink-500">
              <tr>
                <th className="px-4 py-3">Run</th>
                <th className="px-4 py-3">Framework</th>
                <th className="px-4 py-3">Model</th>
                <th className="px-4 py-3">Pass</th>
                <th className="px-4 py-3">Fail</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-900/5">
              {runs.map((r) => (
                <tr key={r.id}>
                  <td className="px-4 py-3 font-medium text-ink-900">{r.id.slice(0, 8)}</td>
                  <td className="px-4 py-3">{r.framework ?? "langgraph"}</td>
                  <td className="px-4 py-3 text-ink-500">{r.model ?? "default"}</td>
                  <td className="px-4 py-3 text-emerald-600">{r.pass_count}</td>
                  <td className="px-4 py-3 text-rose-600">{r.fail_count}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => viewRun(r.id)} className="font-medium text-brand-600">
                      View
                    </button>
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
