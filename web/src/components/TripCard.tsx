import { Link } from "react-router-dom";
import type { TripSummary } from "../types";

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

export function formatDateRange(startDate: string | null, days: number) {
  if (!startDate) return `${days} day${days === 1 ? "" : "s"}`;
  const start = new Date(startDate);
  const end = new Date(start);
  end.setDate(end.getDate() + days);
  const opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
  return `${start.toLocaleDateString(undefined, opts)} – ${end.toLocaleDateString(undefined, opts)}`;
}

export default function TripCard({
  trip,
  readiness,
}: {
  trip: TripSummary;
  /** Optional - how many of the real readiness checks (My Trips command center) this trip has met. */
  readiness?: { done: number; total: number };
}) {
  return (
    <Link
      to={`/trips/${trip.id}`}
      className="group overflow-hidden rounded-xl2 border border-ink-900/5 bg-white shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card-hover"
    >
      <div className={`relative h-28 overflow-hidden bg-gradient-to-br ${coverFor(trip.destination)}`}>
        <div
          aria-hidden="true"
          className="absolute inset-0 bg-gradient-to-t from-black/10 to-transparent transition-opacity duration-200 group-hover:opacity-80"
        />
        <span
          className={`absolute right-3 top-3 rounded-full px-2 py-0.5 text-xs font-medium shadow-sm ${
            statusBadge[trip.status] ?? "bg-white/90 text-ink-700"
          }`}
        >
          {trip.status}
        </span>
      </div>
      <div className="p-4">
        <p className="font-semibold text-ink-900 transition-colors group-hover:text-brand-700">
          {trip.destination}
        </p>
        <p className="mt-1 text-sm text-ink-500">
          {formatDateRange(trip.start_date, trip.days)} · {trip.trip_type}
        </p>
        {readiness && (
          <div className="mt-3">
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-100">
              <div
                className="h-full rounded-full bg-brand-500 transition-all"
                style={{ width: `${(readiness.done / Math.max(readiness.total, 1)) * 100}%` }}
              />
            </div>
            <p className="mt-1.5 text-xs font-medium text-ink-500">
              {readiness.done}/{readiness.total} ready
            </p>
          </div>
        )}
      </div>
    </Link>
  );
}
