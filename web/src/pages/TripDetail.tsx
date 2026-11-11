import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { TripDetail as TripDetailType } from "../types";

type Tab = "itinerary" | "restaurants" | "accommodations";

export default function TripDetail() {
  const { id } = useParams<{ id: string }>();
  const [trip, setTrip] = useState<TripDetailType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("itinerary");

  useEffect(() => {
    if (!id) return;
    api
      .getTrip(id)
      .then(setTrip)
      .catch((e) => setError(e.message));
  }, [id]);

  if (error) return <p className="text-sm text-rose-600">{error}</p>;
  if (!trip) return <p className="text-sm text-ink-500">Loading…</p>;

  return (
    <div>
      <Link to="/trips" className="text-sm text-ink-500 hover:underline">
        ← Back to Trips
      </Link>

      <div className="mt-2 mb-6 flex items-center gap-3">
        <h1 className="text-2xl font-bold">{trip.destination}</h1>
        <span className="rounded-full bg-brand-100 px-2.5 py-1 text-xs font-medium text-brand-700">{trip.status}</span>
      </div>

      <p className="mb-6 text-sm text-ink-500">
        {trip.days} day{trip.days === 1 ? "" : "s"} · {trip.trip_type} · {trip.budget}
        {trip.dietary_preferences.length > 0 && <> · {trip.dietary_preferences.join(", ")}</>}
      </p>

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

      {trip.status === "complete" && trip.plan && (
        <>
          <div className="mb-4 flex gap-2 border-b border-ink-900/10">
            {(["itinerary", "restaurants", "accommodations"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium capitalize ${
                  tab === t ? "border-brand-600 text-brand-700" : "border-transparent text-ink-500 hover:text-ink-900"
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {tab === "itinerary" && (
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
                    {day.activities.length === 0 && <p className="text-sm text-ink-500">No activities scheduled.</p>}
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === "restaurants" && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {trip.plan.restaurants.map((r, i) => (
                <div key={i} className="rounded-xl2 border border-ink-900/5 bg-white p-4">
                  <p className="font-semibold">{r.name}</p>
                  <pre className="mt-1 whitespace-pre-wrap text-xs text-ink-500">
                    {JSON.stringify(r, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          )}

          {tab === "accommodations" && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {trip.plan.accommodations.map((a, i) => (
                <div key={i} className="rounded-xl2 border border-ink-900/5 bg-white p-4">
                  <p className="font-semibold">{a.name}</p>
                  <pre className="mt-1 whitespace-pre-wrap text-xs text-ink-500">
                    {JSON.stringify(a, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
