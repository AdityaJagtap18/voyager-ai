import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { BUDGET_LEVELS, TRIP_TYPES, type FrameworkInfo, type ModelInfo } from "../types";

export default function PlanTrip() {
  const navigate = useNavigate();
  const [destination, setDestination] = useState("");
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
      });
      navigate(`/trips/${trip.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong. Is the backend running?");
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="mb-1 text-2xl font-bold">Plan a Trip</h1>
      <p className="mb-6 text-sm text-ink-500">
        Tell Voyager where you&apos;re headed — the multi-agent workflow researches attractions,
        hotels, restaurants, and builds an optimized day-by-day itinerary.
      </p>

      <form onSubmit={handleSubmit} className="flex flex-col gap-5 rounded-xl2 border border-ink-900/5 bg-white p-6">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Destination
          <input
            required
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            placeholder="e.g. Goa, India"
            className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
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
              className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm font-medium">
            Budget
            <select
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
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
            (optional — when set, accommodation suggestions use real, live hotel pricing instead of AI-generated
            ones)
          </span>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm font-medium">
          Trip type
          <select
            value={tripType}
            onChange={(e) => setTripType(e.target.value)}
            className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            {TRIP_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm font-medium">
          Model <span className="font-normal text-ink-500">(optional — defaults to the server's configured model)</span>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
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
          <select
            value={framework}
            onChange={(e) => setFramework(e.target.value)}
            className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            <option value="">Default (LangGraph)</option>
            {frameworks.map((f) => (
              <option key={f.id} value={f.id} disabled={!f.available}>
                {f.label}
                {f.available ? "" : " (not installed)"}
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
            className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </label>

        {error && <p className="text-sm text-rose-600">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {submitting ? "Planning your trip… this can take a minute" : "Generate Itinerary"}
        </button>
      </form>
    </div>
  );
}
