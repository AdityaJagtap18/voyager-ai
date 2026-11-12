import { useEffect, useState } from "react";
import Spinner from "../components/Spinner";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import type { TraceEntry, TripDetail, TripSummary, WorkflowsResponse } from "../types";

function statusBadge(entry: TraceEntry | undefined) {
  if (!entry) return null;
  if (entry.status === "success") {
    return (
      <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
        ran · {entry.duration_ms.toFixed(0)} ms
      </span>
    );
  }
  if (entry.status === "skipped") {
    return (
      <span className="rounded-full bg-ink-100 px-2 py-0.5 text-xs font-medium text-ink-600">skipped</span>
    );
  }
  return (
    <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-700">error</span>
  );
}

export default function Workflows() {
  const [workflow, setWorkflow] = useState<WorkflowsResponse | null>(null);
  const [trips, setTrips] = useState<TripSummary[] | null>(null);
  const [selectedId, setSelectedId] = useState<string>("");
  const [detail, setDetail] = useState<TripDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getWorkflows(), api.listTrips()])
      .then(([w, t]) => {
        setWorkflow(w);
        setTrips(t);
        const withTrace = t.find((trip) => trip.status !== "planning");
        if (withTrace) setSelectedId(withTrace.id);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    api.getTrip(selectedId).then(setDetail).catch(() => setDetail(null));
  }, [selectedId]);

  function traceFor(stepId: string): TraceEntry | undefined {
    if (!detail) return undefined;
    // Last matching entry - a trip's trace can accumulate more than one run
    // of the same step (e.g. refresh-real-data uses "flights_refresh", a
    // different id, so it never collides with the original plan's "flights").
    const matches = detail.trace.filter((t) => t.step === stepId);
    return matches[matches.length - 1];
  }

  return (
    <div>
      <PageHeader
        icon="AI-Engineering/workflow.svg"
        title="Workflows"
        description="The real planning pipeline every trip runs through - not a separate diagram or builder, the actual node sequence from app/workflow.py (LangGraph) and orchestration/crewai_adapter.py (CrewAI). Pick a trip below to overlay what actually happened on its run."
      />

      {error && <p className="text-sm text-rose-600">{error}</p>}
      {!workflow && !error && <Spinner />}

      {workflow && (
        <>
          <div className="mb-6 grid gap-3 sm:grid-cols-2">
            {workflow.frameworks.map((f) => (
              <div key={f.id} className="rounded-xl2 border border-ink-900/5 bg-white shadow-card p-4">
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
          <p className="mb-6 text-xs text-ink-500">
            Both frameworks run the identical step sequence below - only the engine wiring the steps
            together differs.
          </p>

          <div className="mb-6 flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2 text-sm font-medium text-ink-600">
              Overlay a real run
              <select
                value={selectedId}
                onChange={(e) => setSelectedId(e.target.value)}
                className="rounded-lg border border-ink-900/10 px-2 py-1.5 text-sm"
              >
                <option value="">None (show pipeline only)</option>
                {trips?.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.destination} ({t.days}d)
                  </option>
                ))}
              </select>
            </label>
            {trips && trips.length === 0 && (
              <span className="text-sm text-ink-500">
                No trips yet. <Link to="/plan" className="font-medium text-brand-600">Plan one</Link> to see a real run here.
              </span>
            )}
            {detail && (
              <Link to={`/trips/${detail.id}`} className="text-sm font-medium text-brand-600 hover:underline">
                View this trip →
              </Link>
            )}
          </div>

          <div className="flex flex-col items-stretch gap-0">
            {workflow.steps.map((step, i) => {
              const entry = traceFor(step.id);
              return (
                <div key={step.id} className="flex flex-col items-center">
                  <div className="w-full max-w-xl rounded-xl2 border border-ink-900/5 bg-white shadow-card p-4">
                    <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-ink-900">{step.label}</span>
                        <span className="text-xs text-ink-400">{step.agent}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        {!entry && (
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                              step.always_runs ? "bg-brand-50 text-brand-700" : "bg-ink-100 text-ink-600"
                            }`}
                          >
                            {step.always_runs ? "Always runs" : "Conditional"}
                          </span>
                        )}
                        {statusBadge(entry)}
                      </div>
                    </div>
                    <p className="text-sm text-ink-500">{step.description}</p>
                    {entry?.error && <p className="mt-1 text-xs text-rose-600">{entry.error}</p>}
                  </div>
                  {i < workflow.steps.length - 1 && (
                    <span className="my-1 text-ink-300" aria-hidden="true">
                      ↓
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
