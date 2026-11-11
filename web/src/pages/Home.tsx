import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { TripSummary } from "../types";

const quickLinks = [
  { label: "Flights", sub: "Search & compare", icon: "Travel/flights.svg", to: "/flights" },
  { label: "Hotels", sub: "Find & book", icon: "Travel/hotels.svg", to: "/hotels" },
  { label: "Itinerary", sub: "AI-optimized", icon: "Travel/itinerary.svg", to: "/plan" },
  { label: "Weather", sub: "Forecast & alerts", icon: "Travel/weather.svg", to: "/weather" },
  { label: "Budget", sub: "Plan & track", icon: "Navigation/budget.svg", to: "/budget" },
  { label: "Maps", sub: "Routes & explore", icon: "Travel/map.svg", to: "/maps" },
];

const statusBadge: Record<string, string> = {
  complete: "bg-emerald-100 text-emerald-700",
  planning: "bg-amber-100 text-amber-700",
  failed: "bg-rose-100 text-rose-700",
};

export default function Home() {
  const [trips, setTrips] = useState<TripSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listTrips()
      .then(setTrips)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex flex-col gap-8">
      <section className="overflow-hidden rounded-xl2 bg-gradient-to-r from-brand-600 to-brand-500 px-10 py-14 text-white">
        <h1 className="text-3xl font-bold">Plan · Book · Travel · Build with AI</h1>
        <p className="mt-2 text-brand-50">Your intelligent travel companion and AI engineering playground.</p>
        <div className="mt-6 flex gap-3">
          <Link to="/plan" className="rounded-lg bg-white px-5 py-2.5 text-sm font-semibold text-brand-700 hover:bg-brand-50">
            Plan a Trip
          </Link>
          <Link to="/trips" className="rounded-lg border border-white/40 px-5 py-2.5 text-sm font-semibold text-white hover:bg-white/10">
            My Trips
          </Link>
        </div>
      </section>

      <section className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {quickLinks.map((link) => {
          const content = (
            <>
              <img src={`/icons/${link.icon}`} alt="" className="h-8 w-8" />
              <p className="text-sm font-semibold">{link.label}</p>
              <p className="text-xs text-ink-500">{link.sub}</p>
            </>
          );
          const className =
            "flex flex-col items-center gap-2 rounded-xl2 border border-ink-900/5 bg-white p-4 text-center transition-shadow hover:shadow-md";
          return link.to ? (
            <Link key={link.label} to={link.to} className={className}>
              {content}
            </Link>
          ) : (
            <div key={link.label} className={className + " cursor-default"}>
              {content}
            </div>
          );
        })}
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Your Trips</h2>
          <Link to="/trips" className="text-sm font-medium text-brand-600 hover:underline">
            View All Trips →
          </Link>
        </div>

        {loading && <p className="text-sm text-ink-500">Loading…</p>}
        {error && (
          <p className="text-sm text-rose-600">
            Couldn&apos;t reach the Voyager API at the configured URL ({error}). Is the backend running
            (<code>uvicorn app.api:app --reload</code>)?
          </p>
        )}
        {!loading && !error && trips.length === 0 && (
          <p className="text-sm text-ink-500">No trips yet — plan your first one.</p>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {trips.slice(0, 6).map((trip) => (
            <Link
              key={trip.id}
              to={`/trips/${trip.id}`}
              className="rounded-xl2 border border-ink-900/5 bg-white p-4 transition-shadow hover:shadow-md"
            >
              <div className="mb-2 flex items-center justify-between">
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusBadge[trip.status] ?? "bg-ink-100 text-ink-700"}`}>
                  {trip.status}
                </span>
              </div>
              <p className="font-semibold">{trip.destination}</p>
              <p className="text-sm text-ink-500">
                {trip.days} day{trip.days === 1 ? "" : "s"} · {trip.trip_type}
              </p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
