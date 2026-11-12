import { useEffect, useState } from "react";
import Spinner from "../components/Spinner";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import TripCard from "../components/TripCard";
import type { Booking, TripDetail, TripDocumentSummary, TripSummary } from "../types";

interface TripExtras {
  detail: TripDetail | null;
  bookings: Booking[];
  documents: TripDocumentSummary[];
}

interface ReadinessCheck {
  label: string;
  done: boolean;
}

function computeReadiness(extras: TripExtras): ReadinessCheck[] {
  const { detail, bookings, documents } = extras;
  return [
    { label: "Itinerary planned", done: !!detail && detail.status === "complete" && !!detail.plan },
    { label: "Real flight data found", done: (detail?.plan?.flights?.length ?? 0) > 0 },
    { label: "Accommodation chosen", done: (detail?.plan?.accommodations.length ?? 0) > 0 },
    { label: "Budget target set", done: detail?.budget_amount != null },
    { label: "A booking confirmed", done: bookings.some((b) => b.status === "confirmed") },
    { label: "Travel documents attached", done: documents.length > 0 },
  ];
}

function daysUntil(dateStr: string): number {
  const ms = new Date(dateStr).setHours(0, 0, 0, 0) - new Date().setHours(0, 0, 0, 0);
  return Math.round(ms / (1000 * 60 * 60 * 24));
}

export default function MyTrips() {
  const [trips, setTrips] = useState<TripSummary[]>([]);
  const [extrasByTrip, setExtrasByTrip] = useState<Record<string, TripExtras>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listTrips()
      .then(async (list) => {
        setTrips(list);
        const entries = await Promise.all(
          list.map(async (t) => {
            const [detail, bookings, documents] = await Promise.all([
              api.getTrip(t.id).catch(() => null),
              api.listBookings(t.id).catch(() => []),
              api.listTripDocuments(t.id).catch(() => []),
            ]);
            return [t.id, { detail, bookings, documents }] as const;
          })
        );
        setExtrasByTrip(Object.fromEntries(entries));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const upcoming = trips
    .filter((t) => t.start_date && daysUntil(t.start_date) >= 0)
    .sort((a, b) => daysUntil(a.start_date!) - daysUntil(b.start_date!));

  const alerts = trips.flatMap((t) => {
    if (!t.start_date) return [];
    const days = daysUntil(t.start_date);
    if (days < 0 || days > 14) return [];
    const extras = extrasByTrip[t.id];
    if (!extras) return [];
    const out: string[] = [];
    if (!extras.bookings.some((b) => b.status === "confirmed")) {
      out.push(`${t.destination} starts in ${days} day${days === 1 ? "" : "s"} with no confirmed booking yet.`);
    }
    if (extras.documents.length === 0) {
      out.push(`${t.destination} starts in ${days} day${days === 1 ? "" : "s"} with no travel documents attached.`);
    }
    return out;
  });
  const failedTrips = trips.filter((t) => t.status === "failed");

  return (
    <div>
      <PageHeader icon="Navigation/my-trips.svg" title="My Trips" />
      {loading && <Spinner />}
      {error && <p className="text-sm text-rose-600">{error}</p>}
      {!loading && !error && trips.length === 0 && (
        <p className="text-sm text-ink-500">
          No trips yet. <Link to="/plan" className="text-brand-600 hover:underline">Plan your first one</Link>.
        </p>
      )}

      {!loading && (alerts.length > 0 || failedTrips.length > 0) && (
        <div className="mb-6 rounded-xl2 border border-amber-200 bg-amber-50 p-4 shadow-card">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">Alerts</p>
          <ul className="mt-2 flex flex-col gap-1 text-sm text-amber-900">
            {failedTrips.map((t) => (
              <li key={`failed-${t.id}`}>
                <Link to={`/trips/${t.id}`} className="underline">
                  {t.destination}
                </Link>{" "}
                failed to plan — check its Itinerary tab for the real error.
              </li>
            ))}
            {alerts.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </div>
      )}

      {!loading && upcoming.length > 0 && (
        <div className="mb-6 rounded-xl2 border border-ink-900/5 bg-white shadow-card p-4 shadow-card">
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Upcoming, in order</p>
          <ul className="mt-2 flex flex-col gap-2">
            {upcoming.map((t) => (
              <li key={t.id} className="flex items-center justify-between text-sm">
                <Link to={`/trips/${t.id}`} className="font-medium text-ink-900 hover:underline">
                  {t.destination}
                </Link>
                <span className="text-ink-500">
                  {t.start_date} · in {daysUntil(t.start_date!)} day{daysUntil(t.start_date!) === 1 ? "" : "s"}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {trips.map((trip) => {
          const extras = extrasByTrip[trip.id];
          const checks = extras ? computeReadiness(extras) : null;
          const readiness = checks ? { done: checks.filter((c) => c.done).length, total: checks.length } : undefined;
          return <TripCard key={trip.id} trip={trip} readiness={readiness} />;
        })}
      </div>
    </div>
  );
}
