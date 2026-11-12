import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { TripSummary } from "../types";

const quickLinks = [
  { label: "Flights", sub: "Search & compare", icon: "Travel/flights.svg", to: "/flights", tint: "bg-sky-100" },
  { label: "Hotels", sub: "Find & book", icon: "Travel/hotels.svg", to: "/hotels", tint: "bg-violet-100" },
  { label: "Itinerary", sub: "AI-optimized", icon: "Travel/itinerary.svg", to: "/plan", tint: "bg-amber-100" },
  { label: "Weather", sub: "Forecast & alerts", icon: "Travel/weather.svg", to: "/weather", tint: "bg-cyan-100" },
  { label: "Budget", sub: "Plan & track", icon: "Navigation/budget.svg", to: "/budget", tint: "bg-pink-100" },
  { label: "Maps", sub: "Routes & explore", icon: "Travel/map.svg", to: "/maps", tint: "bg-emerald-100" },
];

const statusBadge: Record<string, string> = {
  complete: "bg-emerald-100 text-emerald-700",
  planning: "bg-amber-100 text-amber-700",
  failed: "bg-rose-100 text-rose-700",
};

// No cover-photo data exists on a trip yet, so each card gets a deterministic
// gradient (by destination name) instead of a fabricated "real" photo.
const covers = [
  "from-sky-500 to-indigo-600",
  "from-violet-500 to-fuchsia-600",
  "from-amber-500 to-orange-600",
  "from-emerald-500 to-teal-600",
  "from-rose-500 to-pink-600",
  "from-cyan-500 to-blue-600",
];

function coverFor(destination: string) {
  let hash = 0;
  for (let i = 0; i < destination.length; i++) hash = (hash * 31 + destination.charCodeAt(i)) % covers.length;
  return covers[hash];
}

function formatDateRange(startDate: string | null, days: number) {
  if (!startDate) return `${days} day${days === 1 ? "" : "s"}`;
  const start = new Date(startDate);
  const end = new Date(start);
  end.setDate(end.getDate() + days);
  const opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
  return `${start.toLocaleDateString(undefined, opts)} – ${end.toLocaleDateString(undefined, opts)}`;
}

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
      <section className="relative isolate overflow-hidden rounded-xl2 bg-gradient-to-br from-indigo-600 via-brand-600 to-sky-600 px-6 py-12 text-white sm:px-10 sm:py-16">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 opacity-25"
          style={{
            backgroundImage:
              "radial-gradient(circle at 15% 25%, white 0%, transparent 35%), radial-gradient(circle at 85% 15%, white 0%, transparent 25%), radial-gradient(circle at 75% 85%, white 0%, transparent 30%)",
          }}
        />
        <div className="relative">
          <h1 className="text-2xl font-bold sm:text-3xl">Plan · Book · Travel · Build with AI</h1>
          <p className="mt-2 text-brand-50">Your intelligent travel companion and AI engineering playground.</p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              to="/plan"
              className="flex items-center gap-2 rounded-lg bg-white px-5 py-2.5 text-sm font-semibold text-brand-700 hover:bg-brand-50"
            >
              <img src="/icons/Travel/flights.svg" alt="" className="h-4 w-4" aria-hidden="true" />
              Plan a Trip
            </Link>
            <Link
              to="/ai/agent-studio"
              className="rounded-lg border border-white/40 bg-white/10 px-5 py-2.5 text-sm font-semibold text-white hover:bg-white/20"
            >
              AI Engineering
            </Link>
            <Link
              to="/trips"
              className="rounded-lg border border-white/40 bg-white/10 px-5 py-2.5 text-sm font-semibold text-white hover:bg-white/20"
            >
              My Trips
            </Link>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {quickLinks.map((link) => (
          <Link
            key={link.label}
            to={link.to}
            className="flex flex-col items-center gap-2 rounded-xl2 border border-ink-900/5 bg-white p-4 text-center transition-shadow hover:shadow-md"
          >
            <span className={`flex h-11 w-11 items-center justify-center rounded-xl ${link.tint}`}>
              <img src={`/icons/${link.icon}`} alt="" className="h-6 w-6" />
            </span>
            <p className="text-sm font-semibold">{link.label}</p>
            <p className="text-xs text-ink-500">{link.sub}</p>
          </Link>
        ))}
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
              className="overflow-hidden rounded-xl2 border border-ink-900/5 bg-white transition-shadow hover:shadow-md"
            >
              <div className={`relative h-28 bg-gradient-to-br ${coverFor(trip.destination)}`}>
                <span
                  className={`absolute right-3 top-3 rounded-full px-2 py-0.5 text-xs font-medium ${
                    statusBadge[trip.status] ?? "bg-white/90 text-ink-700"
                  }`}
                >
                  {trip.status}
                </span>
              </div>
              <div className="p-4">
                <p className="font-semibold">{trip.destination}</p>
                <p className="mt-1 text-sm text-ink-500">
                  {formatDateRange(trip.start_date, trip.days)} · {trip.trip_type}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
