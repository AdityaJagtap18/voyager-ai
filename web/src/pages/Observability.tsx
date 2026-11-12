import { useEffect, useState } from "react";
import Spinner from "../components/Spinner";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import type { ObservabilityOverview, ObservabilitySpan, ObservabilityTraceSummary } from "../types";

type ObsTab = "overview" | "traces";

function StatTile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl2 border border-ink-900/5 bg-white shadow-card p-4">
      <p className="text-xs font-medium text-ink-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-ink-900">{value}</p>
      {sub && <p className="mt-1 text-xs text-ink-500">{sub}</p>}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  if (status === "ok") return <span className="text-emerald-600">✓</span>;
  if (status === "error") return <span className="text-rose-600">✗</span>;
  return <span className="text-ink-300">○</span>;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

/** Humanizes an OTel/auto-instrumentation span name for display - real
 * names as recorded, just presented a bit more readably (e.g. the raw
 * FastAPI/requests auto-instrumentation spans are literally named "GET",
 * "POST", etc. with the real URL only in attributes). */
function spanLabel(span: ObservabilitySpan): string {
  if (span.name === "GET" || span.name === "POST") {
    const url = (span.attributes["http.url"] as string) || (span.attributes["http.target"] as string);
    return url ? `${span.name} ${url}` : span.name;
  }
  return span.name;
}

function SpanTree({
  spans,
  parentId,
  depth,
}: {
  spans: ObservabilitySpan[];
  parentId: string | null;
  depth: number;
}) {
  const children = spans.filter((s) => s.parent_span_id === parentId);
  if (children.length === 0) return null;
  return (
    <div className="flex flex-col gap-1">
      {children.map((span) => (
        <div key={span.span_id}>
          <div
            className="flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-xs hover:bg-ink-900/5"
            style={{ marginLeft: depth * 16 }}
          >
            <span className="flex min-w-0 items-center gap-1.5">
              <StatusBadge status={span.status} />
              <span className="truncate font-medium text-ink-800">{spanLabel(span)}</span>
            </span>
            <span className="shrink-0 text-ink-500">{formatDuration(span.duration_ms)}</span>
          </div>
          <SpanTree spans={spans} parentId={span.span_id} depth={depth + 1} />
        </div>
      ))}
    </div>
  );
}

export default function Observability() {
  const [obsTab, setObsTab] = useState<ObsTab>("overview");
  const [overview, setOverview] = useState<ObservabilityOverview | null>(null);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [traces, setTraces] = useState<ObservabilityTraceSummary[] | null>(null);
  const [tracesError, setTracesError] = useState<string | null>(null);
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [spans, setSpans] = useState<ObservabilitySpan[] | null>(null);
  const [spansError, setSpansError] = useState<string | null>(null);

  useEffect(() => {
    api.observabilityOverview().then(setOverview).catch((e) => setOverviewError(e.message));
    api
      .observabilityTraces(50)
      .then((t) => {
        setTraces(t);
        if (t.length > 0) setSelectedTraceId(t[0].trace_id);
      })
      .catch((e) => setTracesError(e.message));
  }, []);

  useEffect(() => {
    if (!selectedTraceId) return;
    setSpans(null);
    setSpansError(null);
    api.observabilityTrace(selectedTraceId).then(setSpans).catch((e) => setSpansError(e.message));
  }, [selectedTraceId]);

  const latestTrace = traces?.[0];

  return (
    <div>
      <PageHeader
        icon="AI-Engineering/observability.svg"
        title="Observability"
        description="Real OpenTelemetry spans from trip-generation runs — every number here comes from the spans table, not simulated."
      />

      {overview && !overview.otel_enabled && (
        <p className="mb-4 rounded-xl2 border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          OTEL_ENABLED is false on the server — tracing is off, so there's no data to show here. Set it in
          .env and restart the backend to start collecting.
        </p>
      )}
      {overviewError && <p className="mb-4 text-sm text-rose-600">{overviewError}</p>}

      {overview && (
        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          <StatTile label="Total Runs" value={String(overview.total_runs)} />
          <StatTile
            label="Success Rate"
            value={overview.success_rate != null ? `${overview.success_rate}%` : "—"}
          />
          <StatTile
            label="Avg. Latency"
            value={overview.avg_latency_ms != null ? formatDuration(overview.avg_latency_ms) : "—"}
          />
          <StatTile label="LLM Calls" value={String(overview.total_llm_calls)} />
          <StatTile
            label="Total Tokens"
            value={overview.total_tokens != null ? overview.total_tokens.toLocaleString() : "—"}
            sub={overview.total_tokens == null ? "no provider reported usage" : undefined}
          />
        </div>
      )}

      <div className="mb-4 flex gap-1 border-b border-ink-900/10">
        {(["overview", "traces"] as ObsTab[]).map((t) => (
          <button
            key={t}
            onClick={() => setObsTab(t)}
            className={`px-3 pb-2 text-sm font-medium capitalize ${
              obsTab === t ? "border-b-2 border-brand-600 text-brand-700" : "text-ink-500 hover:text-ink-700"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {obsTab === "overview" && (
        <div className="rounded-xl2 border border-ink-900/5 bg-white shadow-card p-5">
          <p className="mb-3 text-sm font-semibold text-ink-900">
            Most recent run{latestTrace ? ` — ${latestTrace.destination ?? latestTrace.trip_id}` : ""}
          </p>
          {tracesError && <p className="text-sm text-rose-600">{tracesError}</p>}
          {!traces && !tracesError && <Spinner />}
          {traces && traces.length === 0 && (
            <p className="text-sm text-ink-500">
              No trip-generation runs recorded yet. <Link to="/plan" className="font-medium text-brand-600">Plan a trip</Link> to see its trace here.
            </p>
          )}
          {latestTrace && spans && <SpanTree spans={spans} parentId={null} depth={0} />}
        </div>
      )}

      {obsTab === "traces" && traces && traces.length > 0 && (
        <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
          <div className="overflow-hidden rounded-xl2 border border-ink-900/5 bg-white shadow-card">
            {traces.map((t) => (
              <button
                key={t.trace_id}
                onClick={() => setSelectedTraceId(t.trace_id)}
                className={`flex w-full flex-col gap-0.5 border-b border-ink-900/5 px-4 py-3 text-left text-sm last:border-b-0 hover:bg-ink-900/5 ${
                  selectedTraceId === t.trace_id ? "bg-brand-50" : ""
                }`}
              >
                <span className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 font-medium text-ink-900">
                    <StatusBadge status={t.status} />
                    {t.destination ?? t.trip_id ?? "Unknown trip"}
                  </span>
                  <span className="shrink-0 text-xs text-ink-500">{formatDuration(t.duration_ms)}</span>
                </span>
                <span className="text-xs text-ink-500">
                  {t.framework ?? "—"} · {t.model ?? "—"}
                </span>
              </button>
            ))}
          </div>

          <div className="rounded-xl2 border border-ink-900/5 bg-white shadow-card p-5">
            {spansError && <p className="text-sm text-rose-600">{spansError}</p>}
            {!spans && !spansError && <Spinner />}
            {spans && (
              <>
                <p className="mb-3 text-xs font-semibold text-ink-600">
                  {spans.length} span{spans.length === 1 ? "" : "s"} in this trace
                </p>
                <SpanTree spans={spans} parentId={null} depth={0} />
                {traces.find((t) => t.trace_id === selectedTraceId)?.trip_id && (
                  <Link
                    to={`/trips/${traces.find((t) => t.trace_id === selectedTraceId)!.trip_id}`}
                    className="mt-4 inline-block text-sm font-medium text-brand-600"
                  >
                    View trip details →
                  </Link>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {obsTab === "traces" && traces && traces.length === 0 && (
        <p className="text-sm text-ink-500">
          No trip-generation runs recorded yet. <Link to="/plan" className="font-medium text-brand-600">Plan a trip</Link> to see its trace here.
        </p>
      )}
    </div>
  );
}
