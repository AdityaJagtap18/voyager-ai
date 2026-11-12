import { FormEvent, useState } from "react";
import { api, ApiError } from "../api/client";
import PageHeader from "../components/PageHeader";
import type { FlightOffer, PlaceSuggestion } from "../types";

function PlacePicker({
  label,
  placeholder,
  value,
  onChange,
}: {
  label: string;
  placeholder: string;
  value: PlaceSuggestion | null;
  onChange: (place: PlaceSuggestion | null) => void;
}) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<PlaceSuggestion[]>([]);
  const [searching, setSearching] = useState(false);

  async function handleQueryChange(q: string) {
    setQuery(q);
    onChange(null);
    if (q.length < 2) {
      setSuggestions([]);
      return;
    }
    setSearching(true);
    try {
      setSuggestions(await api.flightsAutocomplete(q));
    } catch {
      setSuggestions([]);
    } finally {
      setSearching(false);
    }
  }

  return (
    <label className="flex flex-1 min-w-[200px] flex-col gap-1 text-sm font-medium">
      {label}
      <input
        required
        value={value ? `${value.title} (${value.sky_id})` : query}
        onChange={(e) => handleQueryChange(e.target.value)}
        placeholder={placeholder}
        className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
      />
      {!value && suggestions.length > 0 && (
        <div className="rounded-lg border border-ink-900/10 bg-white text-xs shadow-sm">
          {suggestions.map((s, i) => (
            <button
              type="button"
              key={i}
              onClick={() => {
                onChange(s);
                setSuggestions([]);
              }}
              className="block w-full px-3 py-2 text-left hover:bg-ink-900/5"
            >
              {s.title} <span className="text-ink-500">· {s.subtitle}</span>
            </button>
          ))}
        </div>
      )}
      {searching && <p className="text-xs text-ink-500">Searching…</p>}
    </label>
  );
}

export default function Flights() {
  const [origin, setOrigin] = useState<PlaceSuggestion | null>(null);
  const [destination, setDestination] = useState<PlaceSuggestion | null>(null);
  const [departDate, setDepartDate] = useState("");
  const [offers, setOffers] = useState<FlightOffer[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!origin?.sky_id || !destination?.sky_id) {
      setError("Pick an origin and destination from the suggestions.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setOffers(await api.flightsSearch(origin.sky_id, destination.sky_id, departDate));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHeader
        icon="Travel/flights.svg"
        title="Flights"
        description="Real one-way flight search (Phase 3) — live results, not GPT-generated placeholders."
      />

      <form onSubmit={handleSearch} className="mb-8 flex flex-wrap items-end gap-3 rounded-xl2 border border-ink-900/5 bg-white p-6">
        <PlacePicker label="From" placeholder="e.g. Mumbai" value={origin} onChange={setOrigin} />
        <PlacePicker label="To" placeholder="e.g. Goa" value={destination} onChange={setDestination} />
        <label className="flex flex-col gap-1 text-sm font-medium">
          Depart date
          <input
            required
            type="date"
            value={departDate}
            onChange={(e) => setDepartDate(e.target.value)}
            className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm"
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {loading ? "Searching…" : "Search flights"}
        </button>
      </form>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      {offers && (
        <div className="flex flex-col gap-3">
          {offers.length === 0 && <p className="text-sm text-ink-500">No flights found for that route/date.</p>}
          {offers.map((o, i) => (
            <div key={i} className="flex items-center justify-between rounded-xl2 border border-ink-900/5 bg-white p-4">
              <div>
                <p className="font-semibold text-ink-900">
                  {o.origin} → {o.destination} · {o.airline ?? "Unknown airline"}
                </p>
                <p className="text-xs text-ink-500">
                  {o.departure} → {o.arrival} · {o.duration_minutes} min ·{" "}
                  {o.stops === 0 ? "Direct" : `${o.stops} stop(s)`}
                </p>
              </div>
              <p className="text-lg font-bold text-brand-700">{o.price}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
