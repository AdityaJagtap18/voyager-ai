import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { PublicTripView } from "../types";

export default function SharedTrip() {
  const { token } = useParams<{ token: string }>();
  const [trip, setTrip] = useState<PublicTripView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    api
      .getSharedTrip(token)
      .then(setTrip)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Could not load this trip."));
  }, [token]);

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <p className="mb-6 text-xs font-semibold uppercase tracking-wide text-ink-500">Shared trip · read-only</p>

      {error && <p className="text-sm text-rose-600">{error}</p>}
      {!trip && !error && <p className="text-sm text-ink-500">Loading…</p>}

      {trip && (
        <div>
          <h1 className="mb-1 text-2xl font-bold">{trip.destination}</h1>
          <p className="mb-6 text-sm text-ink-500">
            {trip.days} day{trip.days === 1 ? "" : "s"} · {trip.trip_type} · {trip.budget}
          </p>

          {trip.status !== "complete" && (
            <p className="rounded-xl2 border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              This trip's plan isn't ready yet.
            </p>
          )}

          {trip.plan && (
            <div className="flex flex-col gap-4">
              {trip.plan.itinerary?.itinerary?.map((day) => (
                <div key={day.day} className="rounded-xl2 border border-ink-900/5 bg-white p-5">
                  <h3 className="font-semibold">
                    Day {day.day} — {day.theme}
                  </h3>
                  <div className="mt-3 flex flex-col gap-2">
                    {day.activities.map((activity, i) => (
                      <div key={i} className="flex gap-3 border-t border-ink-900/5 pt-2 first:border-t-0 first:pt-0">
                        <span className="w-16 shrink-0 text-xs font-medium text-ink-500">{activity.time}</span>
                        <div>
                          <p className="text-sm font-medium">{activity.name}</p>
                          {activity.description && <p className="text-xs text-ink-500">{activity.description}</p>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
