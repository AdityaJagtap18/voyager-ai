import { useEffect, useState } from "react";
import Spinner from "../components/Spinner";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import TripAssistant from "../components/TripAssistant";
import TripBookings from "../components/TripBookings";
import TripBudget from "../components/TripBudget";
import TripDocuments from "../components/TripDocuments";
import TripShare from "../components/TripShare";
import DayMap from "../components/DayMap";
import type { TripDetail as TripDetailType, RecommendationTag, TransportMode, AccommodationRecommendationTag } from "../types";

const TRANSPORT_MODE_LABELS: Record<TransportMode, string> = {
  walk: "Walk",
  cycle: "Cycle",
  taxi_or_transit: "Taxi / transit",
  dedicated_transfer: "Dedicated transfer",
};

type Tab =
  | "itinerary"
  | "flights"
  | "transportation"
  | "restaurants"
  | "accommodations"
  | "bookings"
  | "budget"
  | "documents"
  | "share"
  | "assistant";

export default function TripDetail() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const requestedTab = searchParams.get("tab") as Tab | null;
  const [trip, setTrip] = useState<TripDetailType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>(requestedTab ?? "itinerary");
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const [selectingIndex, setSelectingIndex] = useState<number | null>(null);
  const [refreshingRealData, setRefreshingRealData] = useState(false);
  const [refreshResult, setRefreshResult] = useState<string | null>(null);
  const [displayCurrency, setDisplayCurrency] = useState<string>("");
  const [rateCache, setRateCache] = useState<Record<string, number>>({});
  const [rateLoading, setRateLoading] = useState(false);

  const flightCurrencies = Array.from(new Set((trip?.plan?.flights ?? []).map((f) => f.currency))).filter(Boolean);
  const accommodationCurrencies = Array.from(
    new Set(
      (trip?.plan?.accommodations ?? [])
        .filter((a) => a.source === "real")
        .map((a) => a.currency as string | undefined)
        .filter((c): c is string => Boolean(c))
    )
  );
  const offerCurrencies = Array.from(new Set([...flightCurrencies, ...accommodationCurrencies]));

  useEffect(() => {
    if (!displayCurrency || offerCurrencies.length === 0) return;
    const missing = offerCurrencies.filter((c) => c !== displayCurrency && !(`${c}->${displayCurrency}` in rateCache));
    if (missing.length === 0) return;
    setRateLoading(true);
    Promise.all(
      missing.map((c) =>
        api
          .convertCurrency(1, c, displayCurrency)
          .then((r) => [`${c}->${displayCurrency}`, r.rate] as const)
          .catch(() => null)
      )
    )
      .then((results) => {
        setRateCache((prev) => {
          const next = { ...prev };
          for (const r of results) if (r) next[r[0]] = r[1];
          return next;
        });
      })
      .finally(() => setRateLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [displayCurrency, offerCurrencies.join(",")]);

  function convertedPrice(amount: number | null, fromCurrency: string): { amount: number; currency: string } | null {
    if (amount == null) return null;
    if (!displayCurrency || fromCurrency === displayCurrency) return { amount, currency: fromCurrency };
    const rate = rateCache[`${fromCurrency}->${displayCurrency}`];
    if (rate == null) return null;
    return { amount: Math.round(amount * rate * 100) / 100, currency: displayCurrency };
  }

  function formatDateTime(iso: string | null): string {
    if (!iso) return "N/A";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function refresh() {
    if (!id) return;
    api
      .getTrip(id)
      .then((t) => {
        setTrip(t);
        if (!t.plan && !requestedTab) setTab("bookings");
      })
      .catch((e) => setError(e.message));
  }

  useEffect(refresh, [id, requestedTab]);

  async function handleSelectFlight(index: number) {
    if (!id) return;
    setSelectingIndex(index);
    try {
      const updated = await api.selectFlight(id, index);
      setTrip(updated);
    } finally {
      setSelectingIndex(null);
    }
  }

  async function handleSelectAccommodation(index: number) {
    if (!id) return;
    setSelectingIndex(index);
    try {
      const updated = await api.selectAccommodation(id, index);
      setTrip(updated);
    } finally {
      setSelectingIndex(null);
    }
  }

  async function handleRefreshRealData() {
    if (!id) return;
    setRefreshingRealData(true);
    setRefreshResult(null);
    try {
      const updated = await api.refreshRealData(id);
      setTrip(updated);
      const latest = updated.trace.slice(-3);
      const refreshed = latest
        .filter((t) => t.status === "success")
        .map((t) => t.step.replace("_refresh", ""));
      setRefreshResult(
        refreshed.length > 0
          ? `Refreshed: ${refreshed.join(", ")}.`
          : "No new real data found yet — providers still have nothing to offer for this trip."
      );
    } catch (e) {
      setRefreshResult(e instanceof Error ? e.message : "Refresh failed.");
    } finally {
      setRefreshingRealData(false);
    }
  }

  if (error) return <p className="text-sm text-rose-600">{error}</p>;
  if (!trip) return <Spinner />;

  return (
    <div>
      <Link to="/trips" className="text-sm text-ink-500 hover:underline">
        ← Back to Trips
      </Link>

      <div className="mt-2 mb-1 flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-50">
          <img src="/icons/Travel/itinerary.svg" alt="" className="h-5 w-5" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-bold">{trip.destination}</h1>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            <span className="rounded-full bg-brand-100 px-2.5 py-1 text-xs font-medium text-brand-700">
              {trip.status}
            </span>
            {trip.model && (
              <span className="rounded-full bg-ink-900/5 px-2.5 py-1 text-xs font-medium text-ink-500">
                {trip.model}
              </span>
            )}
            {trip.framework && (
              <span className="rounded-full bg-ink-900/5 px-2.5 py-1 text-xs font-medium text-ink-500">
                {trip.framework}
              </span>
            )}
          </div>
        </div>
      </div>

      <p className="mb-2 ml-12 text-sm text-ink-500">
        {trip.days} day{trip.days === 1 ? "" : "s"} · {trip.trip_type} · {trip.budget}
        {trip.dietary_preferences.length > 0 && <> · {trip.dietary_preferences.join(", ")}</>}
      </p>

      {trip.plan && (
        <div className="mb-6 ml-12 flex flex-wrap items-center gap-2">
          <button
            onClick={handleRefreshRealData}
            disabled={refreshingRealData}
            className="rounded-full border border-ink-900/10 px-3 py-1 text-xs font-medium hover:bg-brand-50 disabled:opacity-50"
          >
            {refreshingRealData ? "Refreshing…" : "Refresh real data"}
          </button>
          <span className="text-xs text-ink-400">
            Re-tries live flight/hotel/transfer lookups — useful if a provider was down or rate-limited
            when this trip was first planned.
          </span>
          {refreshResult && <span className="w-full text-xs font-medium text-ink-600">{refreshResult}</span>}
        </div>
      )}

      {trip.status === "planning" && (
        <p className="rounded-xl2 border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          Still planning — refresh in a moment.
        </p>
      )}

      {trip.status === "failed" && (
        <div className="rounded-xl2 border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          <p className="font-semibold">Planning failed</p>
          <ul className="mt-1 list-disc pl-5">
            {trip.errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      {trip.status !== "planning" && (
        <>
          <div className="relative mb-4 border-b border-ink-900/10">
            <div className="flex gap-2 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {(trip.plan
              ? ([
                  "itinerary",
                  "flights",
                  "restaurants",
                  "accommodations",
                  "bookings",
                  "budget",
                  "documents",
                  "share",
                  "assistant",
                ] as Tab[])
              : (["bookings", "budget", "documents", "share", "assistant"] as Tab[])
            ).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`-mb-px shrink-0 border-b-2 px-3 py-2 text-sm font-medium capitalize ${
                  tab === t ? "border-brand-600 text-brand-700" : "border-transparent text-ink-500 hover:text-ink-900"
                }`}
              >
                {t === "bookings"
                  ? "Bookings & Wallet"
                  : t === "budget"
                  ? "Budget & Expenses"
                  : t === "assistant"
                  ? "Ask Voyager"
                  : t}
              </button>
            ))}
            </div>
            <div
              aria-hidden="true"
              className="pointer-events-none absolute right-0 top-0 bottom-px w-8 bg-gradient-to-l from-white to-transparent"
            />
          </div>

          {tab === "bookings" && <TripBookings tripId={trip.id} />}
          {tab === "budget" && (
            <TripBudget
              tripId={trip.id}
              budgetAmount={trip.budget_amount}
              plan={trip.plan}
              budgetAllocation={trip.budget_allocation}
            />
          )}
          {tab === "documents" && <TripDocuments tripId={trip.id} />}
          {tab === "share" && <TripShare tripId={trip.id} initialToken={trip.share_token} />}
          {tab === "assistant" && <TripAssistant tripId={trip.id} />}

          {tab === "itinerary" && trip.plan && (() => {
            const days = trip.plan.itinerary?.itinerary ?? [];
            const activeDay = days.find((d) => d.day === selectedDay) ?? days[0];

            // Every line here is derived from data already loaded for this
            // trip - no new fetches, no invented percentages. Anything we
            // can't actually check from real data is left out rather than
            // guessed (per the "never fabricate metrics" rule).
            const insights: string[] = [];
            const totalWarnings = days.reduce((sum, d) => sum + (d.warnings?.length ?? 0), 0);
            insights.push(
              totalWarnings === 0
                ? "No scheduling conflicts across the trip"
                : `${totalWarnings} scheduling conflict${totalWarnings === 1 ? "" : "s"} flagged - see day warnings`
            );
            if (trip.accommodation_recommendations) {
              insights.push(
                trip.accommodation_recommendations.any_in_budget
                  ? "At least one accommodation fits your budget cap"
                  : "No accommodation fits under your nightly budget cap - showing closest options"
              );
            }
            if (trip.flight_recommendations) {
              insights.push(
                trip.flight_recommendations.any_in_budget
                  ? "At least one flight fits your budget cap"
                  : "No flight fits under your budget cap - showing closest options"
              );
            }
            const dayStops = activeDay?.activities.length ?? 0;
            const dayGeocoded = activeDay?.activities.filter((a) => a.coordinates).length ?? 0;
            if (dayStops > 0) {
              insights.push(
                dayGeocoded === dayStops
                  ? `All ${dayStops} of today's stops are mapped with real coordinates`
                  : `${dayGeocoded} of ${dayStops} of today's stops are mapped with real coordinates`
              );
            }

            return (
              <div className="flex flex-col gap-4">
                {days.length > 1 && (
                  <div className="flex flex-wrap gap-2">
                    {days.map((day) => (
                      <button
                        key={day.day}
                        onClick={() => setSelectedDay(day.day)}
                        className={`rounded-xl2 border px-4 py-2 text-left text-xs font-medium ${
                          (activeDay?.day ?? days[0]?.day) === day.day
                            ? "border-brand-500 bg-brand-50 text-brand-700"
                            : "border-ink-900/10 bg-white text-ink-600 hover:bg-ink-50"
                        }`}
                      >
                        Day {day.day}
                      </button>
                    ))}
                  </div>
                )}
                {activeDay && (
                  <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
                    <div className="rounded-xl2 border border-ink-900/5 bg-white shadow-card p-5 lg:col-span-3">
                      <h3 className="font-semibold">
                        Day {activeDay.day} — {activeDay.theme}
                      </h3>
                      {activeDay.warnings && activeDay.warnings.length > 0 && (
                        <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-800">
                          {activeDay.warnings.map((w, i) => (
                            <p key={i}>{w}</p>
                          ))}
                        </div>
                      )}
                      <div className="mt-3 flex flex-col gap-2">
                        {activeDay.activities.map((activity, i) => (
                          <div key={i} className="flex gap-3 border-t border-ink-900/5 pt-2 first:border-t-0 first:pt-0">
                            <span className="w-16 shrink-0 text-xs font-medium text-ink-500">{activity.time}</span>
                            <div className="min-w-0 flex-1">
                              <div className="flex flex-wrap items-center gap-1.5">
                                <p className="text-sm font-medium">{activity.name}</p>
                                {activity.scheduling_status === "conflict" && (
                                  <span className="rounded-full bg-rose-100 px-1.5 py-0.5 text-[10px] font-medium text-rose-700">
                                    Scheduling conflict
                                  </span>
                                )}
                                {activity.time_source === "estimated" && (
                                  <span className="rounded-full bg-ink-100 px-1.5 py-0.5 text-[10px] font-medium text-ink-500">
                                    Estimated time
                                  </span>
                                )}
                              </div>
                              {activity.description && <p className="text-xs text-ink-500">{activity.description}</p>}
                              <p className="mt-0.5 text-xs text-ink-400">
                                {activity.duration && <>{activity.duration}</>}
                                {!!activity.travel_time_before_minutes && (
                                  <> · {activity.travel_time_before_minutes} min travel before this</>
                                )}
                              </p>
                            </div>
                          </div>
                        ))}
                        {activeDay.activities.length === 0 && (
                          <p className="text-sm text-ink-500">No activities scheduled.</p>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col gap-4 lg:col-span-2">
                      {insights.length > 0 && (
                        <div className="rounded-xl2 border border-brand-100 bg-brand-50/60 p-4">
                          <p className="mb-2 text-xs font-semibold text-brand-700">Trip insights</p>
                          <ul className="flex flex-col gap-1.5">
                            {insights.map((insight, i) => (
                              <li key={i} className="flex gap-1.5 text-xs text-ink-700">
                                <span className="text-brand-600">✓</span>
                                {insight}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      <div className="rounded-xl2 border border-ink-900/5 bg-white shadow-card p-4">
                        <p className="mb-2 text-xs font-semibold text-ink-600">Day {activeDay.day} route</p>
                        <DayMap activities={activeDay.activities} />
                      </div>
                    </div>
                  </div>
                )}
                {days.length === 0 && (
                  <p className="rounded-xl2 border border-ink-900/5 bg-white shadow-card p-4 text-sm text-ink-500">
                    No itinerary generated for this trip.
                  </p>
                )}
              </div>
            );
          })()}

          {tab === "flights" && trip.plan && (
            <div className="flex flex-col gap-3">
              {(!trip.plan.flights || trip.plan.flights.length === 0) && (
                <p className="rounded-xl2 border border-ink-900/5 bg-white shadow-card p-4 text-sm text-ink-500">
                  No real flight data for this trip.{" "}
                  {trip.origin
                    ? "The live flight search found no offers, or the provider errored — nothing was invented to fill the gap."
                    : "Add a departure city and start date to a new trip to ground it in a real flight search."}
                </p>
              )}
              {flightCurrencies.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 rounded-xl2 border border-ink-900/5 bg-white shadow-card p-3">
                  <label className="flex items-center gap-2 text-xs font-medium text-ink-600">
                    Show prices in
                    <select
                      value={displayCurrency}
                      onChange={(e) => setDisplayCurrency(e.target.value)}
                      className="rounded-lg border border-ink-900/10 px-2 py-1 text-xs"
                    >
                      <option value="">Original ({flightCurrencies.join(", ")})</option>
                      {["USD", "EUR", "GBP", "INR", "JPY", "AUD", "CAD", "SGD"]
                        .filter((c) => !flightCurrencies.includes(c))
                        .map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                    </select>
                  </label>
                  {rateLoading && <span className="text-xs text-ink-400">Fetching live rate…</span>}
                  {displayCurrency && !rateLoading && (
                    <span className="text-xs text-ink-400">Converted at live exchange rates — never estimated.</span>
                  )}
                </div>
              )}
              {trip.flight_recommendations && (
                <div className="rounded-xl2 border border-brand-100 bg-brand-50/60 p-3 text-xs text-ink-700">
                  <p className="font-semibold text-brand-700">
                    Recommendations use {trip.flight_recommendations.traveler_count} traveler
                    {trip.flight_recommendations.traveler_count === 1 ? "" : "s"}
                    {trip.flight_recommendations.max_flight_budget != null &&
                      ` · flight budget cap ${trip.flight_recommendations.max_flight_budget}`}
                  </p>
                  {!trip.flight_recommendations.any_in_budget && trip.flight_recommendations.max_flight_budget != null && (
                    <p className="mt-1 text-amber-700">
                      No offer fits under the flight budget cap — showing the closest options for comparison anyway.
                    </p>
                  )}
                  {trip.flight_recommendations.assumptions.map((a, i) => (
                    <p key={i} className="mt-1 text-ink-500">
                      {a}
                    </p>
                  ))}
                </div>
              )}
              {trip.plan.flights?.map((f, i) => {
                const bookingUrl =
                  trip.origin && trip.start_date
                    ? `https://www.google.com/travel/flights?q=${encodeURIComponent(
                        `Flights from ${f.origin_query ?? trip.origin} to ${f.destination_query ?? trip.destination} on ${trip.start_date}`
                      )}`
                    : null;
                const isSelected = trip.selected_flight_index === i;
                const recs = trip.flight_recommendations;
                const tags = recs
                  ? (Object.entries(recs.recommended) as [RecommendationTag, number | undefined][])
                      .filter(([, idx]) => idx === i)
                      .map(([tag]) => tag)
                  : [];
                const scored = recs?.offers.find((o) => o.index === i);
                return (
                  <div
                    key={i}
                    className={`rounded-xl2 border bg-white shadow-card p-4 ${isSelected ? "border-brand-500 ring-1 ring-brand-500" : "border-ink-900/5"}`}
                  >
                    {tags.length > 0 && (
                      <div className="mb-2 flex flex-wrap gap-1.5">
                        {tags.map((tag) => (
                          <span
                            key={tag}
                            title={recs?.reasons[tag]}
                            className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                              tag === "best_overall" ? "bg-amber-100 text-amber-800" : "bg-sky-100 text-sky-700"
                            }`}
                          >
                            {recs?.labels[tag]}
                          </span>
                        ))}
                      </div>
                    )}
                    {tags.length > 0 && recs && (
                      <p className="mb-2 text-xs text-ink-500">{recs.reasons[tags[0]]}</p>
                    )}
                    {scored && scored.within_budget === false && (
                      <p className="mb-2 text-xs font-medium text-rose-600">Over your flight budget cap</p>
                    )}
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <p className="font-semibold">
                        {f.airline ?? "Unknown airline"} · {f.origin} → {f.destination}
                      </p>
                      <div className="flex shrink-0 items-center gap-2">
                        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                          Live offer
                        </span>
                        {isSelected ? (
                          <span className="rounded-full bg-brand-100 px-2 py-0.5 text-xs font-medium text-brand-700">
                            Selected
                          </span>
                        ) : (
                          <button
                            onClick={() => handleSelectFlight(i)}
                            disabled={selectingIndex !== null}
                            className="rounded-full border border-ink-900/10 px-2 py-0.5 text-xs font-medium hover:bg-brand-50 disabled:opacity-50"
                          >
                            {selectingIndex === i ? "Selecting…" : "Select"}
                          </button>
                        )}
                      </div>
                    </div>
                    <p className="text-sm text-ink-700">
                      {(() => {
                        const converted = convertedPrice(f.price_raw, f.currency);
                        if (converted) return `${converted.currency} ${converted.amount}`;
                        return f.price ?? "Price unavailable";
                      })()}
                      {displayCurrency && displayCurrency !== f.currency && (
                        <span className="ml-1 text-xs text-ink-400">({f.price ?? `${f.currency} ${f.price_raw}`})</span>
                      )}
                      {" · "}
                      {f.stops === 0 ? "Nonstop" : `${f.stops} stop(s)`}
                      {f.duration_minutes != null && ` · ${Math.round(f.duration_minutes / 60)}h ${f.duration_minutes % 60}m`}
                    </p>
                    {scored?.total_price != null && recs && recs.traveler_count > 1 && (
                      <p className="text-xs text-ink-500">
                        {(() => {
                          const converted = convertedPrice(scored.total_price, f.currency);
                          return converted
                            ? `${converted.currency} ${converted.amount}`
                            : `${f.currency} ${scored.total_price}`;
                        })()}{" "}
                        total for {recs.traveler_count} travelers
                      </p>
                    )}
                    <p className="mt-1 text-xs text-ink-500">
                      Departs {formatDateTime(f.departure)} · Arrives {formatDateTime(f.arrival)}
                    </p>
                    {bookingUrl && (
                      <a
                        href={bookingUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:underline"
                      >
                        Search &amp; book on Google Flights →
                      </a>
                    )}
                    <p className="mt-1 text-xs text-ink-400">
                      Opens a prefilled search — Voyager can't link directly to this exact offer, and no booking is
                      completed here.
                    </p>
                  </div>
                );
              })}
            </div>
          )}

          {tab === "transportation" && trip.plan && (
            <div className="flex flex-col gap-3">
              {!trip.plan.transportation && !trip.transport_recommendations?.local_transport.length && (
                <p className="rounded-xl2 border border-ink-900/5 bg-white shadow-card p-4 text-sm text-ink-500">
                  No real transfer route for this trip. This only covers an airport-to-accommodation
                  drive, and only once accommodation is chosen — it needs an accommodation with coordinates.
                  Rental cars, taxi fares, and public transit aren't integrated (no provider), so nothing
                  for those is shown here, real or estimated.
                </p>
              )}

              {trip.transport_recommendations && (
                <div className="rounded-xl2 border border-brand-100 bg-brand-50/50 p-4 text-xs text-ink-600">
                  {trip.transport_recommendations.assumptions.map((a, i) => (
                    <p key={i} className={i > 0 ? "mt-1" : ""}>
                      {a}
                    </p>
                  ))}
                </div>
              )}

              {trip.plan.transportation && (
                <div className="rounded-xl2 border border-ink-900/5 bg-white shadow-card p-4">
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <p className="font-semibold">
                      {trip.plan.transportation.from} → {trip.plan.transportation.to}
                    </p>
                    <span className="shrink-0 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                      Real route
                    </span>
                  </div>
                  <p className="text-sm text-ink-700">
                    {trip.plan.transportation.distance_km} km · {trip.plan.transportation.duration_h.toFixed(1)}h
                    driving
                  </p>
                  {trip.transport_recommendations?.airport_transfer && (
                    <div className="mt-2 flex items-center gap-2">
                      <span className="shrink-0 rounded-full bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-800">
                        Recommended: {TRANSPORT_MODE_LABELS[trip.transport_recommendations.airport_transfer.recommended_mode]}
                      </span>
                      <p className="text-xs text-ink-500">{trip.transport_recommendations.airport_transfer.reason}</p>
                    </div>
                  )}
                  <p className="mt-2 text-xs text-ink-400">
                    A real routed distance/duration, not a fare — no rental-car, taxi, or public-transit
                    pricing provider is integrated, so no price is shown or estimated.
                  </p>
                </div>
              )}

              {trip.transport_recommendations && trip.transport_recommendations.local_transport.length > 0 && (
                <div className="rounded-xl2 border border-ink-900/5 bg-white shadow-card p-4">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">
                    Local transport between stops
                  </p>
                  <div className="flex flex-col gap-2">
                    {trip.transport_recommendations.local_transport.map((hop, i) => (
                      <div key={i} className="flex flex-wrap items-center gap-2 border-t border-ink-900/5 pt-2 first:border-t-0 first:pt-0">
                        <span className="shrink-0 rounded-full bg-ink-100 px-2 py-0.5 text-xs font-medium text-ink-700">
                          Day {hop.day}
                        </span>
                        <p className="text-sm">
                          {hop.from ?? "Start"} → {hop.to ?? "End"}{" "}
                          <span className="text-ink-500">({hop.distance_km} km)</span>
                        </p>
                        <span className="shrink-0 rounded-full bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-800">
                          {TRANSPORT_MODE_LABELS[hop.recommended_mode]}
                        </span>
                        <p className="w-full text-xs text-ink-400">{hop.reason}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {tab === "restaurants" && trip.plan && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {trip.plan.restaurants.map((r, i) => (
                <div key={i} className="rounded-xl2 border border-ink-900/5 bg-white shadow-card p-4">
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <p className="font-semibold">{r.name}</p>
                    {r.source === "real" ? (
                      <span className="shrink-0 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                        Live listing
                      </span>
                    ) : (
                      <span className="shrink-0 rounded-full bg-ink-100 px-2 py-0.5 text-xs font-medium text-ink-700">
                        AI suggestion
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-ink-600">
                    {[r.cuisine, r.price_range].filter(Boolean).join(" · ")}
                  </p>
                  {r.location && <p className="mt-1 text-xs text-ink-500">{r.location}</p>}
                  {r.description && <p className="mt-2 text-sm text-ink-700">{r.description}</p>}
                  {r.reservation && (
                    <p className="mt-2 text-xs font-medium text-ink-500">
                      Reservation: <span className="font-normal capitalize">{r.reservation}</span>
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {tab === "accommodations" && trip.plan && (
            <div className="flex flex-col gap-3">
              <p className="text-xs text-ink-500">
                Selecting an accommodation recomputes only the Itinerary tab's day-by-day schedule
                (it depends on where you're staying) — flights, research, and dining aren't touched.
              </p>
              {accommodationCurrencies.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 rounded-xl2 border border-ink-900/5 bg-white shadow-card p-3">
                  <label className="flex items-center gap-2 text-xs font-medium text-ink-600">
                    Show prices in
                    <select
                      value={displayCurrency}
                      onChange={(e) => setDisplayCurrency(e.target.value)}
                      className="rounded-lg border border-ink-900/10 px-2 py-1 text-xs"
                    >
                      <option value="">Original ({accommodationCurrencies.join(", ")})</option>
                      {["USD", "EUR", "GBP", "INR", "JPY", "AUD", "CAD", "SGD"]
                        .filter((c) => !accommodationCurrencies.includes(c))
                        .map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                    </select>
                  </label>
                  {rateLoading && <span className="text-xs text-ink-400">Fetching live rate…</span>}
                  {displayCurrency && !rateLoading && (
                    <span className="text-xs text-ink-400">Converted at live exchange rates — never estimated.</span>
                  )}
                </div>
              )}
              {trip.accommodation_recommendations && (
                <div className="rounded-xl2 border border-brand-100 bg-brand-50/60 p-3 text-xs text-ink-700">
                  <p className="font-semibold text-brand-700">
                    Recommendations use {trip.accommodation_recommendations.nights} night
                    {trip.accommodation_recommendations.nights === 1 ? "" : "s"}
                  </p>
                  {!trip.accommodation_recommendations.any_in_budget &&
                    trip.accommodation_recommendations.max_nightly_budget != null && (
                      <p className="mt-1 text-amber-700">
                        No listing fits under the nightly budget cap — showing the closest options for comparison anyway.
                      </p>
                    )}
                  {trip.accommodation_recommendations.assumptions.map((a, i) => (
                    <p key={i} className="mt-1 text-ink-500">
                      {a}
                    </p>
                  ))}
                </div>
              )}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {trip.plan.accommodations.map((a, i) => {
                  const isSelected = trip.selected_accommodation_index === i;
                  const converted =
                    a.source === "real" && a.currency
                      ? convertedPrice(a.price_raw ?? null, a.currency)
                      : null;
                  const accRecs = trip.accommodation_recommendations;
                  const accTags = accRecs
                    ? (Object.entries(accRecs.recommended) as [AccommodationRecommendationTag, number | undefined][])
                        .filter(([, idx]) => idx === i)
                        .map(([tag]) => tag)
                    : [];
                  return (
                    <div
                      key={i}
                      className={`rounded-xl2 border bg-white p-4 ${isSelected ? "border-brand-500 ring-1 ring-brand-500" : "border-ink-900/5"}`}
                    >
                      {accTags.length > 0 && (
                        <div className="mb-2 flex flex-wrap gap-1.5">
                          {accTags.map((tag) => (
                            <span
                              key={tag}
                              title={accRecs?.reasons[tag]}
                              className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                                tag === "best_overall" ? "bg-amber-100 text-amber-800" : "bg-sky-100 text-sky-700"
                              }`}
                            >
                              {accRecs?.labels[tag]}
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <p className="font-semibold">{String(a.name)}</p>
                        <div className="flex shrink-0 items-center gap-2">
                          {a.source === "real" ? (
                            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                              Live pricing
                            </span>
                          ) : (
                            <span className="rounded-full bg-ink-100 px-2 py-0.5 text-xs font-medium text-ink-700">
                              AI suggestion
                            </span>
                          )}
                          {isSelected ? (
                            <span className="rounded-full bg-brand-100 px-2 py-0.5 text-xs font-medium text-brand-700">
                              Selected
                            </span>
                          ) : (
                            <button
                              onClick={() => handleSelectAccommodation(i)}
                              disabled={selectingIndex !== null}
                              className="rounded-full border border-ink-900/10 px-2 py-0.5 text-xs font-medium hover:bg-brand-50 disabled:opacity-50"
                            >
                              {selectingIndex === i ? "Recalculating…" : "Select"}
                            </button>
                          )}
                        </div>
                      </div>
                      {accTags.length > 0 && accRecs && (
                        <p className="mb-2 text-xs text-ink-500">{accRecs.reasons[accTags[0]]}</p>
                      )}
                      {converted ? (
                        <p className="text-sm font-medium text-ink-700">
                          {converted.currency} {converted.amount} / night
                          {displayCurrency && displayCurrency !== a.currency && (
                            <span className="ml-1 text-xs font-normal text-ink-400">
                              ({a.currency} {a.price_raw})
                            </span>
                          )}
                        </p>
                      ) : (
                        a.price_per_night && (
                          <p className="text-sm font-medium text-ink-700">{a.price_per_night} / night</p>
                        )
                      )}
                      <p className="mt-1 text-xs text-ink-500">
                        {[a.type, a.neighborhood || a.location, a.rating].filter(Boolean).join(" · ")}
                      </p>
                      {a.highlights && a.highlights.length > 0 && (
                        <p className="mt-2 text-sm text-ink-700">{a.highlights.join(" · ")}</p>
                      )}
                      {a.amenities && a.amenities.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {a.amenities.map((amenity) => (
                            <span
                              key={amenity}
                              className="rounded-full bg-ink-100 px-2 py-0.5 text-xs text-ink-600"
                            >
                              {amenity}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
