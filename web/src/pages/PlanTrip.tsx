import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import PageHeader from "../components/PageHeader";
import { BUDGET_LEVELS, TRIP_TYPES, type FrameworkInfo, type ModelInfo } from "../types";

const fieldClass =
  "rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";

const pipelineSteps = [
  { label: "Research", sub: "Finds attractions near your destination", icon: "AI-Engineering/agent.svg" },
  { label: "Flights", sub: "Searches real flights when you give an origin + date", icon: "Travel/flights.svg" },
  { label: "Accommodation", sub: "Ranks hotels by proximity to those attractions", icon: "Travel/hotels.svg" },
  { label: "Transportation", sub: "Routes a real airport-to-hotel transfer time", icon: "Travel/map.svg" },
  { label: "Dining", sub: "Finds restaurants, honoring dietary preferences", icon: "Travel/restaurant.svg" },
  { label: "Itinerary", sub: "Builds the optimized day-by-day schedule", icon: "Travel/itinerary.svg" },
];

export default function PlanTrip() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [destination, setDestination] = useState(() => searchParams.get("destination") ?? "");
  const [origin, setOrigin] = useState("");
  const [days, setDays] = useState(3);
  const [tripType, setTripType] = useState<string>(TRIP_TYPES[0]);
  const [budget, setBudget] = useState<string>("mid-range");
  const [startDate, setStartDate] = useState("");
  const [dietary, setDietary] = useState("");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [model, setModel] = useState<string>("");
  const [frameworks, setFrameworks] = useState<FrameworkInfo[]>([]);
  const [framework, setFramework] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listModels()
      .then(setModels)
      .catch(() => setModels([]));
    api
      .listFrameworks()
      .then(setFrameworks)
      .catch(() => setFrameworks([]));
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const trip = await api.createTrip({
        destination,
        days,
        trip_type: tripType,
        budget,
        dietary_preferences: dietary
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        model: model || undefined,
        framework: framework || undefined,
        start_date: startDate || undefined,
        origin: origin || undefined,
      });
      navigate(`/trips/${trip.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong. Is the backend running?");
      setSubmitting(false);
    }
  }

  return (
    <div>
      <PageHeader
        icon="Navigation/plan-trip.svg"
        title="Plan a Trip"
        description="Tell Voyager where you're headed — the multi-agent workflow researches attractions, hotels, restaurants, and builds an optimized day-by-day itinerary."
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <form onSubmit={handleSubmit} className="flex flex-col gap-6 rounded-xl2 border border-ink-900/5 bg-white shadow-card p-6">
          <div className="flex flex-col gap-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Trip basics</p>
            <label className="flex flex-col gap-1 text-sm font-medium">
              Destination
              <input
                required
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                placeholder="e.g. Goa, India"
                className={fieldClass}
              />
            </label>

            <div className="grid grid-cols-2 gap-4">
              <label className="flex flex-col gap-1 text-sm font-medium">
                Days
                <input
                  type="number"
                  min={1}
                  max={30}
                  required
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                  className={fieldClass}
                />
              </label>

              <label className="flex flex-col gap-1 text-sm font-medium">
                Budget
                <select value={budget} onChange={(e) => setBudget(e.target.value)} className={fieldClass}>
                  {BUDGET_LEVELS.map((b) => (
                    <option key={b} value={b}>
                      {b}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <label className="flex flex-col gap-1 text-sm font-medium">
              Start date{" "}
              <span className="font-normal text-ink-500">
                (optional — when set, accommodation suggestions use real, live hotel pricing instead of
                AI-generated ones)
              </span>
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className={fieldClass} />
            </label>

            <label className="flex flex-col gap-1 text-sm font-medium">
              Departure from{" "}
              <span className="font-normal text-ink-500">
                (optional — with a start date, grounds the trip in a real flight search instead of no flight data)
              </span>
              <input
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                placeholder="e.g. Mumbai"
                className={fieldClass}
              />
            </label>
          </div>

          <div className="flex flex-col gap-4 border-t border-ink-900/5 pt-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Trip style</p>
            <label className="flex flex-col gap-1 text-sm font-medium">
              Trip type
              <select value={tripType} onChange={(e) => setTripType(e.target.value)} className={fieldClass}>
                {TRIP_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1 text-sm font-medium">
              Dietary preferences <span className="font-normal text-ink-500">(optional, comma-separated)</span>
              <input
                value={dietary}
                onChange={(e) => setDietary(e.target.value)}
                placeholder="vegetarian, gluten-free"
                className={fieldClass}
              />
            </label>
          </div>

          <div className="flex flex-col gap-4 border-t border-ink-900/5 pt-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Advanced (AI Engineering)</p>
            <label className="flex flex-col gap-1 text-sm font-medium">
              Model <span className="font-normal text-ink-500">(optional — defaults to the server's configured model)</span>
              <select value={model} onChange={(e) => setModel(e.target.value)} className={fieldClass}>
                <option value="">Default</option>
                {models.map((m) => (
                  <option key={m.id} value={m.id} disabled={!m.configured}>
                    {m.label}
                    {m.configured ? "" : " (needs API key)"}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1 text-sm font-medium">
              Orchestration framework{" "}
              <span className="font-normal text-ink-500">(optional — see Agent Studio)</span>
              <select value={framework} onChange={(e) => setFramework(e.target.value)} className={fieldClass}>
                <option value="">Default (LangGraph)</option>
                {frameworks.map((f) => (
                  <option key={f.id} value={f.id} disabled={!f.available}>
                    {f.label}
                    {f.available ? "" : " (not installed)"}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {error && <p className="text-sm text-rose-600">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          >
            <img src="/icons/Travel/flights.svg" alt="" className="h-4 w-4 invert" aria-hidden="true" />
            {submitting ? "Planning your trip… this can take a minute" : "Generate Itinerary"}
          </button>
        </form>

        <aside className="flex flex-col gap-4">
          <div className="rounded-xl2 border border-ink-900/5 bg-white shadow-card p-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Preview</p>
            <p className="mt-2 text-lg font-semibold text-ink-900">{destination || "Your destination"}</p>
            <p className="text-sm text-ink-500">
              {days} day{days === 1 ? "" : "s"} · {tripType} · {budget}
            </p>
            {startDate && <p className="mt-1 text-xs text-ink-500">Starting {startDate}</p>}
            {origin && <p className="mt-1 text-xs text-ink-500">Flying from {origin}</p>}
          </div>

          <div className="rounded-xl2 border border-ink-900/5 bg-white shadow-card p-5">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-ink-500">
              What Voyager runs for you
            </p>
            <div className="flex flex-col gap-3">
              {pipelineSteps.map((step) => (
                <div key={step.label} className="flex items-start gap-3">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-50">
                    <img src={`/icons/${step.icon}`} alt="" className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <div>
                    <p className="text-sm font-medium text-ink-900">{step.label}</p>
                    <p className="text-xs text-ink-500">{step.sub}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
