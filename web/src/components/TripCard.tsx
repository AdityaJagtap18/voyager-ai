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
  onDelete,
}: {
  trip: TripSummary;
  /** Optional - how many of the real readiness checks (My Trips command center) this trip has met. */
  readiness?: { done: number; total: number };
  /** Optional - shows a delete button on the card (top-left) when provided. */
  onDelete?: (trip: TripSummary) => void;
}) {
  return (
    <Link
      to={`/trips/${trip.id}`}
      className="group relative overflow-hidden rounded-xl2 border border-ink-900/5 bg-white shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card-hover"
    >
      <div className={`relative h-28 overflow-hidden bg-gradient-to-br ${coverFor(trip.destination)}`}>
        <div
          aria-hidden="true"
          className="absolute inset-0 bg-gradient-to-t from-black/10 to-transparent transition-opacity duration-200 group-hover:opacity-80"
        />
        {onDelete && (
          <button
            type="button"
            aria-label={`Delete ${trip.destination} trip`}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onDelete(trip);
            }}
            className="absolute left-3 top-3 rounded-full bg-black/30 p-1.5 text-white opacity-0 transition-opacity hover:bg-rose-600 group-hover:opacity-100"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5">
              <path
                fillRule="evenodd"
                d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 3.993V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        )}
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
