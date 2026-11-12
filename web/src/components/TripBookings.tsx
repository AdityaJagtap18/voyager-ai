import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";
import { BOOKING_TYPES, type Booking } from "../types";

const statusBadge: Record<string, string> = {
  confirmed: "bg-emerald-100 text-emerald-700",
  pending: "bg-amber-100 text-amber-700",
  cancelled: "bg-rose-100 text-rose-700",
};

export default function TripBookings({ tripId }: { tripId: string }) {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);
  const [type, setType] = useState<string>(BOOKING_TYPES[0]);
  const [title, setTitle] = useState("");
  const [reference, setReference] = useState("");
  const [cost, setCost] = useState("");

  function refresh() {
    api.listBookings(tripId).then(setBookings).finally(() => setLoading(false));
  }

  useEffect(refresh, [tripId]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    await api.createBooking(tripId, {
      type,
      title,
      reference: reference || undefined,
      cost: cost ? Number(cost) : undefined,
    });
    setTitle("");
    setReference("");
    setCost("");
    refresh();
  }

  return (
    <div className="flex flex-col gap-6">
      <form onSubmit={handleAdd} className="flex flex-wrap items-end gap-3 rounded-xl2 border border-ink-900/5 bg-white shadow-card p-4">
        <label className="flex flex-col gap-1 text-xs font-medium">
          Type
          <select value={type} onChange={(e) => setType(e.target.value)} className="rounded-lg border border-ink-900/10 px-2 py-1.5 text-sm">
            {BOOKING_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-1 min-w-[180px] flex-col gap-1 text-xs font-medium">
          Title
          <input
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Indigo 6E123, Mumbai → Goa"
            className="rounded-lg border border-ink-900/10 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Reference
          <input
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            placeholder="PNR / confirmation #"
            className="w-36 rounded-lg border border-ink-900/10 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Cost (₹)
          <input
            type="number"
            min={0}
            value={cost}
            onChange={(e) => setCost(e.target.value)}
            className="w-28 rounded-lg border border-ink-900/10 px-2 py-1.5 text-sm"
          />
        </label>
        <button type="submit" className="rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-brand-700">
          Add
        </button>
      </form>

      {loading && <p className="text-sm text-ink-500">Loading…</p>}
      {!loading && bookings.length === 0 && <p className="text-sm text-ink-500">No bookings recorded yet.</p>}

      <div className="flex flex-col gap-3">
        {bookings.map((b) => (
          <div key={b.id} className="flex items-center justify-between rounded-xl2 border border-ink-900/5 bg-white shadow-card p-4">
            <div>
              <p className="font-semibold capitalize">
                {b.type} — {b.title}
              </p>
              <p className="text-xs text-ink-500">
                {b.reference && <>Ref: {b.reference} · </>}
                {b.cost != null && <>₹{b.cost.toLocaleString()}</>}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={b.status}
                onChange={(e) => api.updateBookingStatus(tripId, b.id, e.target.value).then(refresh)}
                className={`rounded-full border-0 px-2.5 py-1 text-xs font-medium ${statusBadge[b.status]}`}
              >
                <option value="pending">pending</option>
                <option value="confirmed">confirmed</option>
                <option value="cancelled">cancelled</option>
              </select>
              <button
                onClick={() => api.deleteBooking(tripId, b.id).then(refresh)}
                className="text-xs text-ink-500 hover:text-rose-600"
              >
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
