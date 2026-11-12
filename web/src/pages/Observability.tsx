import { useEffect, useState } from "react";
import Spinner from "../components/Spinner";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import type {
  EvaluationRunSummary,
  ObservabilityAgentStats,
  ObservabilityLogEntry,
  ObservabilityModelStats,
  ObservabilityOverview,
  ObservabilitySpan,
  ObservabilityTraceSummary,
} from "../types";

type ObsTab = "overview" | "traces" | "agents" | "models" | "evaluations" | "logs";

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
  const [agents, setAgents] = useState<ObservabilityAgentStats[] | null>(null);
  const [agentsError, setAgentsError] = useState<string | null>(null);
  const [models, setModels] = useState<ObservabilityModelStats[] | null>(null);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const [evalRuns, setEvalRuns] = useState<EvaluationRunSummary[] | null>(null);
  const [evalRunsError, setEvalRunsError] = useState<string | null>(null);
  const [logs, setLogs] = useState<ObservabilityLogEntry[] | null>(null);
  const [logsTotal, setLogsTotal] = useState(0);
  const [logsError, setLogsError] = useState<string | null>(null);
  const [logStatusFilter, setLogStatusFilter] = useState<string>("");
  const [logNameFilter, setLogNameFilter] = useState<string>("");

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

  useEffect(() => {
    if (obsTab === "agents" && !agents) {
      api.observabilityAgents().then(setAgents).catch((e) => setAgentsError(e.message));
    }
    if (obsTab === "models" && !models) {
      api.observabilityModels().then(setModels).catch((e) => setModelsError(e.message));
    }
    if (obsTab === "evaluations" && !evalRuns) {
      api.listEvaluationRuns().then(setEvalRuns).catch((e) => setEvalRunsError(e.message));
    }
  }, [obsTab, agents, models, evalRuns]);

  useEffect(() => {
    if (obsTab !== "logs") return;
    setLogs(null);
    setLogsError(null);
    api
      .observabilityLogs(50, 0, logStatusFilter || undefined, logNameFilter || undefined)
      .then((r) => {
        setLogs(r.items);
        setLogsTotal(r.total);
      })
      .catch((e) => setLogsError(e.message));
  }, [obsTab, logStatusFilter, logNameFilter]);

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
        {(["overview", "traces", "agents", "models", "evaluations", "logs"] as ObsTab[]).map((t) => (
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

      {obsTab === "agents" && (
        <div className="overflow-hidden rounded-xl2 border border-ink-900/5 bg-white shadow-card">
          {agentsError && <p className="p-5 text-sm text-rose-600">{agentsError}</p>}
          {!agents && !agentsError && <div className="p-5"><Spinner /></div>}
          {agents && agents.length === 0 && (
            <p className="p-5 text-sm text-ink-500">No agent spans recorded yet.</p>
          )}
          {agents && agents.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ink-900/5 text-left text-xs font-medium text-ink-500">
                  <th className="px-4 py-3">Agent</th>
                  <th className="px-4 py-3">Calls</th>
                  <th className="px-4 py-3">Avg. duration</th>
                  <th className="px-4 py-3">Errors</th>
                </tr>
              </thead>
              <tbody>
                {agents.map((a) => (
                  <tr key={a.name} className="border-b border-ink-900/5 last:border-b-0">
                    <td className="px-4 py-3 font-medium text-ink-900">{a.name}</td>
                    <td className="px-4 py-3 text-ink-700">{a.call_count}</td>
                    <td className="px-4 py-3 text-ink-700">{formatDuration(a.avg_duration_ms)}</td>
                    <td className={`px-4 py-3 ${a.error_count > 0 ? "text-rose-600" : "text-ink-700"}`}>{a.error_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {obsTab === "models" && (
        <div className="overflow-hidden rounded-xl2 border border-ink-900/5 bg-white shadow-card">
          {modelsError && <p className="p-5 text-sm text-rose-600">{modelsError}</p>}
          {!models && !modelsError && <div className="p-5"><Spinner /></div>}
          {models && models.length === 0 && (
            <p className="p-5 text-sm text-ink-500">No LLM calls recorded yet.</p>
          )}
          {models && models.length > 0 && (
            <>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-ink-900/5 text-left text-xs font-medium text-ink-500">
                    <th className="px-4 py-3">Model</th>
                    <th className="px-4 py-3">Calls</th>
                    <th className="px-4 py-3">Avg. duration</th>
                    <th className="px-4 py-3">Input tokens</th>
                    <th className="px-4 py-3">Output tokens</th>
                    <th className="px-4 py-3">Est. cost</th>
                  </tr>
                </thead>
                <tbody>
                  {models.map((m) => (
                    <tr key={m.model} className="border-b border-ink-900/5 last:border-b-0">
                      <td className="px-4 py-3 font-medium text-ink-900">{m.model}</td>
                      <td className="px-4 py-3 text-ink-700">{m.call_count}</td>
                      <td className="px-4 py-3 text-ink-700">{formatDuration(m.avg_duration_ms)}</td>
                      <td className="px-4 py-3 text-ink-700">{m.total_input_tokens?.toLocaleString() ?? "—"}</td>
                      <td className="px-4 py-3 text-ink-700">{m.total_output_tokens?.toLocaleString() ?? "—"}</td>
                      <td className="px-4 py-3 text-ink-700">
                        {m.estimated_cost_usd != null ? `$${m.estimated_cost_usd.toFixed(4)}` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="border-t border-ink-900/5 p-3 text-xs text-ink-400">
                Estimated from app/pricing.py's published per-token rates; "—" means pricing is unknown for that
                model or some calls in the group are missing token counts.
              </p>
            </>
          )}
        </div>
      )}

      {obsTab === "evaluations" && (
        <div className="rounded-xl2 border border-ink-900/5 bg-white shadow-card p-5">
          {evalRunsError && <p className="text-sm text-rose-600">{evalRunsError}</p>}
          {!evalRuns && !evalRunsError && <Spinner />}
          {evalRuns && evalRuns.length === 0 && (
            <p className="text-sm text-ink-500">
              No evaluation runs yet. Run the canned case suite from{" "}
              <Link to="/ai/evaluations" className="font-medium text-brand-600">Evaluations</Link>.
            </p>
          )}
          {evalRuns && evalRuns.length > 0 && (
            <>
              <div className="flex flex-col gap-2">
                {evalRuns.slice(0, 10).map((r) => (
                  <div key={r.id} className="flex items-center justify-between rounded-lg border border-ink-900/5 px-3 py-2 text-sm">
                    <span className="font-medium text-ink-900">
                      {r.framework ?? "—"} · {r.model ?? "—"}
                    </span>
                    <span className="text-ink-500">
                      <span className="text-emerald-600">{r.pass_count} passed</span>
                      {r.fail_count > 0 && <span className="ml-2 text-rose-600">{r.fail_count} failed</span>}
                    </span>
                  </div>
                ))}
              </div>
              <Link to="/ai/evaluations" className="mt-4 inline-block text-sm font-medium text-brand-600">
                View all evaluation runs →
              </Link>
            </>
          )}
        </div>
      )}

      {obsTab === "logs" && (
        <div className="rounded-xl2 border border-ink-900/5 bg-white shadow-card">
          <div className="flex flex-wrap gap-2 border-b border-ink-900/5 p-3">
            <select
              value={logStatusFilter}
              onChange={(e) => setLogStatusFilter(e.target.value)}
              className="rounded-lg border border-ink-900/10 px-2 py-1 text-sm"
            >
              <option value="">All statuses</option>
              <option value="ok">ok</option>
              <option value="error">error</option>
              <option value="unset">unset</option>
            </select>
            <input
              value={logNameFilter}
              onChange={(e) => setLogNameFilter(e.target.value)}
              placeholder="Filter by span name..."
              className="flex-1 rounded-lg border border-ink-900/10 px-2 py-1 text-sm"
            />
          </div>
          {logsError && <p className="p-5 text-sm text-rose-600">{logsError}</p>}
          {!logs && !logsError && <div className="p-5"><Spinner /></div>}
          {logs && logs.length === 0 && <p className="p-5 text-sm text-ink-500">No spans match this filter.</p>}
          {logs && logs.length > 0 && (
            <>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-ink-900/5 text-left text-xs font-medium text-ink-500">
                    <th className="px-4 py-2">Name</th>
                    <th className="px-4 py-2">Status</th>
                    <th className="px-4 py-2">Duration</th>
                    <th className="px-4 py-2">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((l) => (
                    <tr key={l.span_id} className="border-b border-ink-900/5 last:border-b-0">
                      <td className="px-4 py-2 font-mono text-xs text-ink-800">{l.name}</td>
                      <td className="px-4 py-2"><StatusBadge status={l.status} /></td>
                      <td className="px-4 py-2 text-ink-700">{formatDuration(l.duration_ms)}</td>
                      <td className="px-4 py-2 text-xs text-ink-500">{new Date(l.start_time).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="border-t border-ink-900/5 p-3 text-xs text-ink-400">
                Showing {logs.length} of {logsTotal} spans.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
