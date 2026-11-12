import { FormEvent, useState } from "react";
import { api, ApiError } from "../api/client";
import PageHeader from "../components/PageHeader";
import type { HotelOffer, PlaceSuggestion } from "../types";

export default function Hotels() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<PlaceSuggestion[]>([]);
  const [destination, setDestination] = useState<PlaceSuggestion | null>(null);
  const [checkin, setCheckin] = useState("");
  const [checkout, setCheckout] = useState("");
  const [offers, setOffers] = useState<HotelOffer[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleQueryChange(q: string) {
    setQuery(q);
    setDestination(null);
    if (q.length < 2) {
      setSuggestions([]);
      return;
    }
    try {
      setSuggestions(await api.hotelsAutocomplete(q));
    } catch {
      setSuggestions([]);
    }
  }

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!destination?.dest_id || !destination.search_type) {
      setError("Pick a destination from the suggestions.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setOffers(await api.hotelsSearch(destination.dest_id, destination.search_type, checkin, checkout));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHeader
        icon="Travel/hotels.svg"
        title="Hotels"
        description="Real hotel search (Phase 3) — live availability and pricing, not GPT-generated placeholders."
      />

      <form onSubmit={handleSearch} className="mb-8 flex flex-wrap items-end gap-3 rounded-xl2 border border-ink-900/5 bg-white shadow-card p-6">
        <label className="relative flex w-full min-w-[220px] flex-1 flex-col gap-1 text-sm font-medium sm:w-auto">
          Destination
          <input
            required
            value={destination ? destination.label : query}
            onChange={(e) => handleQueryChange(e.target.value)}
            placeholder="e.g. Goa"
            className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          {!destination && suggestions.length > 0 && (
            <div className="absolute top-full z-10 mt-1 w-full rounded-lg border border-ink-900/10 bg-white text-xs shadow-sm">
              {suggestions.map((s, i) => (
                <button
                  type="button"
                  key={i}
                  onClick={() => {
                    setDestination(s);
                    setSuggestions([]);
                  }}
                  className="block w-full px-3 py-2 text-left hover:bg-ink-900/5"
                >
                  {s.label}
                </button>
              ))}
            </div>
          )}
        </label>
        <label className="flex w-full flex-col gap-1 text-sm font-medium sm:w-auto">
          Check-in
          <input
            required
            type="date"
            value={checkin}
            onChange={(e) => setCheckin(e.target.value)}
            className="w-full rounded-lg border border-ink-900/10 px-3 py-2 text-sm"
          />
        </label>
        <label className="flex w-full flex-col gap-1 text-sm font-medium sm:w-auto">
          Check-out
          <input
            required
            type="date"
            value={checkout}
            onChange={(e) => setCheckout(e.target.value)}
            className="w-full rounded-lg border border-ink-900/10 px-3 py-2 text-sm"
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50 sm:w-auto"
        >
          {loading ? "Searching…" : "Search hotels"}
        </button>
      </form>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      {offers && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {offers.length === 0 && <p className="text-sm text-ink-500">No hotels found for those dates.</p>}
          {offers.map((h) => (
            <div key={h.hotel_id} className="overflow-hidden rounded-xl2 border border-ink-900/5 bg-white shadow-card">
              {h.photo_url && <img src={h.photo_url} alt={h.name ?? ""} className="h-36 w-full object-cover" />}
              <div className="p-4">
                <p className="font-semibold text-ink-900">{h.name}</p>
                <p className="text-xs text-ink-500">
                  {h.review_score_word ?? "—"} {h.review_score != null && `· ${h.review_score}/10`}
                  {h.star_rating != null && ` · ${h.star_rating}★`}
                </p>
                <p className="mt-2 text-lg font-bold text-brand-700">{h.price_formatted}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
