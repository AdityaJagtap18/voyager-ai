import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import TripCard from "../components/TripCard";
import type { TripSummary } from "../types";

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
      <PageHeader icon="Navigation/my-trips.svg" title="My Trips" />
      {loading && <p className="text-sm text-ink-500">Loading…</p>}
      {error && <p className="text-sm text-rose-600">{error}</p>}
      {!loading && !error && trips.length === 0 && (
        <p className="text-sm text-ink-500">
          No trips yet. <Link to="/plan" className="text-brand-600 hover:underline">Plan your first one</Link>.
        </p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {trips.map((trip) => (
          <TripCard key={trip.id} trip={trip} />
        ))}
      </div>
    </div>
  );
}
