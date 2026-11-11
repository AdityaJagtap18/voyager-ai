import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { TripSummary } from "../types";

/**
 * Bookings & Wallet and Budget & Expenses are per-trip (Section 3 of the
 * blueprint keeps bookings/expenses scoped to a trip, not a single global
 * ledger). This hub lets the sidebar link go somewhere real: pick a trip,
 * land on that tab in Trip Detail — rather than a dead "coming soon" page.
 */
export default function TripPickerHub({ title, description, tab }: { title: string; description: string; tab: "bookings" | "budget" }) {
  const [trips, setTrips] = useState<TripSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listTrips().then(setTrips).finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold">{title}</h1>
      <p className="mb-6 text-sm text-ink-500">{description}</p>

      {loading && <p className="text-sm text-ink-500">Loading…</p>}
      {!loading && trips.length === 0 && (
        <p className="text-sm text-ink-500">
          No trips yet. <Link to="/plan" className="text-brand-600 hover:underline">Plan one first</Link>, then come back here.
        </p>
      )}

      <div className="flex flex-col gap-3">
        {trips.map((trip) => (
          <Link
            key={trip.id}
            to={`/trips/${trip.id}?tab=${tab}`}
            className="flex items-center justify-between rounded-xl2 border border-ink-900/5 bg-white p-4 hover:shadow-md"
          >
            <div>
              <p className="font-semibold">{trip.destination}</p>
              <p className="text-sm text-ink-500">
                {trip.days} day{trip.days === 1 ? "" : "s"} · {trip.trip_type}
              </p>
            </div>
            <span className="text-sm font-medium text-brand-600">Open →</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
