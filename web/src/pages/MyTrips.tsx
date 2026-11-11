import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { TripSummary } from "../types";

const statusBadge: Record<string, string> = {
  complete: "bg-emerald-100 text-emerald-700",
  planning: "bg-amber-100 text-amber-700",
  failed: "bg-rose-100 text-rose-700",
};

export default function MyTrips() {
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
    <div>
      <h1 className="mb-6 text-2xl font-bold">My Trips</h1>
      {loading && <p className="text-sm text-ink-500">Loading…</p>}
      {error && <p className="text-sm text-rose-600">{error}</p>}
      {!loading && !error && trips.length === 0 && (
        <p className="text-sm text-ink-500">
          No trips yet. <Link to="/plan" className="text-brand-600 hover:underline">Plan your first one</Link>.
        </p>
      )}

      <div className="flex flex-col gap-3">
        {trips.map((trip) => (
          <Link
            key={trip.id}
            to={`/trips/${trip.id}`}
            className="flex items-center justify-between rounded-xl2 border border-ink-900/5 bg-white p-4 hover:shadow-md"
          >
            <div>
              <p className="font-semibold">{trip.destination}</p>
              <p className="text-sm text-ink-500">
                {trip.days} day{trip.days === 1 ? "" : "s"} · {trip.trip_type} · {trip.budget}
              </p>
            </div>
            <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusBadge[trip.status] ?? "bg-ink-100 text-ink-700"}`}>
              {trip.status}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
