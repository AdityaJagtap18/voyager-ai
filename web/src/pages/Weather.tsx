import { FormEvent, useState } from "react";
import { api, ApiError } from "../api/client";
import PageHeader from "../components/PageHeader";
import type { WeatherForecast } from "../types";

export default function Weather() {
  const [destination, setDestination] = useState("");
  const [forecast, setForecast] = useState<WeatherForecast | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      setForecast(await api.weatherForecast(destination));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHeader
        icon="Travel/weather.svg"
        title="Weather"
        description="Real forecast data from OpenWeatherMap (Phase 3) — the free tier only looks 5 days ahead, so a trip further out won't show a full-length forecast here."
      />

      <form onSubmit={handleSearch} className="mb-8 flex flex-wrap items-end gap-3 rounded-xl2 border border-ink-900/5 bg-white p-6">
        <label className="flex flex-1 min-w-[220px] flex-col gap-1 text-sm font-medium">
          Destination
          <input
            required
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            placeholder="e.g. Goa, India"
            className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {loading ? "Loading…" : "Get forecast"}
        </button>
      </form>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      {forecast && (
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-500">
            {forecast.location.name}
            {forecast.location.country ? `, ${forecast.location.country}` : ""}
          </h2>
          {forecast.days.length === 0 && <p className="text-sm text-ink-500">No forecast data available.</p>}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {forecast.days.map((d) => (
              <div key={d.date} className="rounded-xl2 border border-ink-900/5 bg-white p-4 text-center">
                <p className="text-xs font-medium text-ink-500">{d.date}</p>
                {d.icon && (
                  <img
                    src={`https://openweathermap.org/img/wn/${d.icon}@2x.png`}
                    alt={d.description ?? ""}
                    className="mx-auto h-12 w-12"
                  />
                )}
                <p className="text-sm font-semibold text-ink-900">
                  {d.temp_max}° / {d.temp_min}°
                </p>
                {d.description && <p className="text-xs capitalize text-ink-500">{d.description}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
