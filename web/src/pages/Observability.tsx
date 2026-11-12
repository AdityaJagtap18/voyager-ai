import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import type { TripSummary, TripDetail } from "../types";

function StatusDot({ status }: { status: string }) {
  const color =
    status === "complete" ? "bg-emerald-500" : status === "failed" ? "bg-rose-500" : "bg-amber-500";
  return <span className={`inline-block h-2 w-2 rounded-full ${color}`} />;
}

function StatTile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl2 border border-ink-900/5 bg-white p-4">
      <p className="text-xs font-medium text-ink-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-ink-900">{value}</p>
      {sub && <p className="mt-1 text-xs text-ink-500">{sub}</p>}
    </div>
  );
}

export default function Observability() {
  const [trips, setTrips] = useState<TripSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<TripDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [allDetails, setAllDetails] = useState<TripDetail[]>([]);

  useEffect(() => {
    api
      .listTrips()
      .then((t) => {
        setTrips(t);
        if (t.length > 0) setSelectedId(t[0].id);
        // Real aggregate stats below are computed from these - not simulated.
        Promise.all(t.map((trip) => api.getTrip(trip.id).catch(() => null))).then((details) =>
          setAllDetails(details.filter((d): d is TripDetail => d !== null))
        );
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setDetail(null);
    setDetailError(null);
    api
      .getTrip(selectedId)
      .then(setDetail)
      .catch((e) => setDetailError(e.message));
  }, [selectedId]);

  const totalMs = detail?.trace.reduce((sum, t) => sum + t.duration_ms, 0) ?? 0;

  const runsWithTrace = allDetails.filter((d) => d.trace.length > 0);
  const totalRuns = runsWithTrace.length;
  const allSteps = runsWithTrace.flatMap((d) => d.trace);
  const successRate = allSteps.length ? (allSteps.filter((s) => s.status === "success").length / allSteps.length) * 100 : 0;
  const avgLatencyMs = runsWithTrace.length
    ? runsWithTrace.reduce((sum, d) => sum + d.trace.reduce((s, t) => s + t.duration_ms, 0), 0) / runsWithTrace.length
    : 0;
  const failedSteps = allSteps.filter((s) => s.status !== "success").length;

  return (
    <div>
      <PageHeader
        icon="AI-Engineering/observability.svg"
        title="Observability"
        description="Per-agent timing and status for each trip's planning run — which step was slow, which step failed, and how long the whole plan took, for either orchestration framework. These numbers come straight from the trace stored on each trip; there's no separate tracing backend (LangSmith/Langfuse etc. aren't wired up yet)."
      />

      {error && <p className="text-sm text-rose-600">{error}</p>}

      {trips && trips.length > 0 && (
        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatTile label="Total Runs" value={String(totalRuns)} />
          <StatTile label="Success Rate" value={allSteps.length ? `${successRate.toFixed(1)}%` : "—"} />
          <StatTile label="Avg. Duration" value={avgLatencyMs ? `${(avgLatencyMs / 1000).toFixed(1)}s` : "—"} />
          <StatTile label="Failed Steps" value={String(failedSteps)} sub={failedSteps ? "across all runs" : undefined} />
        </div>
      )}

      {trips && trips.length === 0 && !error && (
        <p className="text-sm text-ink-500">
          No trips yet. <Link to="/plan" className="font-medium text-brand-600">Plan one</Link> to see its trace here.
        </p>
      )}

      {trips && trips.length > 0 && (
        <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
          <div className="overflow-hidden rounded-xl2 border border-ink-900/5 bg-white">
            {trips.map((t) => (
              <button
                key={t.id}
                onClick={() => setSelectedId(t.id)}
                className={`flex w-full items-center justify-between gap-2 border-b border-ink-900/5 px-4 py-3 text-left text-sm last:border-b-0 hover:bg-ink-900/5 ${
                  selectedId === t.id ? "bg-brand-50" : ""
                }`}
              >
                <span className="flex items-center gap-2">
                  <StatusDot status={t.status} />
                  <span className="font-medium text-ink-900">{t.destination}</span>
                </span>
                <span className="text-xs text-ink-500">{t.days}d</span>
              </button>
            ))}
          </div>

          <div>
            {detailError && <p className="text-sm text-rose-600">{detailError}</p>}
            {!detail && !detailError && <p className="text-sm text-ink-500">Loading…</p>}
            {detail && (
              <div className="rounded-xl2 border border-ink-900/5 bg-white p-6">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-ink-900">{detail.destination}</h2>
                    <p className="text-xs text-ink-500">
                      {detail.framework ?? "langgraph"} · {detail.model ?? "default model"}
                    </p>
                  </div>
                  <span className="text-sm font-medium text-ink-500">{totalMs.toFixed(0)} ms total</span>
                </div>

                {detail.trace.length === 0 && (
                  <p className="text-sm text-ink-500">No trace recorded for this trip.</p>
                )}

                {detail.trace.length > 0 && (
                  <div className="flex flex-col gap-2">
                    {detail.trace.map((entry, i) => (
                      <div key={i} className="rounded-lg border border-ink-900/10 p-3">
                        <div className="mb-1 flex items-center justify-between text-sm">
                          <span className="font-medium capitalize text-ink-900">{entry.step}</span>
                          <span
                            className={
                              entry.status === "success" ? "text-emerald-600" : "text-rose-600"
                            }
                          >
                            {entry.status === "success" ? "ok" : "error"} · {entry.duration_ms.toFixed(0)} ms
                          </span>
                        </div>
                        <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-900/5">
                          <div
                            className={`h-full ${entry.status === "success" ? "bg-brand-500" : "bg-rose-500"}`}
                            style={{ width: `${totalMs ? (entry.duration_ms / totalMs) * 100 : 0}%` }}
                          />
                        </div>
                        {entry.error && <p className="mt-1 text-xs text-rose-600">{entry.error}</p>}
                      </div>
                    ))}
                  </div>
                )}

                <Link to={`/trips/${detail.id}`} className="mt-4 inline-block text-sm font-medium text-brand-600">
                  View trip details →
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
