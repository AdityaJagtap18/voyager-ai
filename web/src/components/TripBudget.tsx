import { FormEvent, useEffect, useState } from "react";
import Spinner from "./Spinner";
import { api } from "../api/client";
import { EXPENSE_CATEGORIES, type Booking, type TripExpense, type TripPlan } from "../types";

function cheapestReal<T extends { source?: unknown }>(items: T[] | undefined, priceOf: (item: T) => number | null) {
  if (!items) return null;
  let best: { item: T; price: number } | null = null;
  for (const item of items) {
    if (item.source !== "real") continue;
    const price = priceOf(item);
    if (price == null) continue;
    if (!best || price < best.price) best = { item, price };
  }
  return best;
}

export default function TripBudget({
  tripId,
  budgetAmount,
  plan,
}: {
  tripId: string;
  budgetAmount: number | null;
  plan: TripPlan | null;
}) {
  const [expenses, setExpenses] = useState<TripExpense[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);
  const [budgetInput, setBudgetInput] = useState(budgetAmount?.toString() ?? "");
  const [category, setCategory] = useState<string>(EXPENSE_CATEGORIES[0]);
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [currentBudget, setCurrentBudget] = useState(budgetAmount);

  function refresh() {
    Promise.all([api.listExpenses(tripId), api.listBookings(tripId)])
      .then(([e, b]) => {
        setExpenses(e);
        setBookings(b);
      })
      .finally(() => setLoading(false));
  }

  useEffect(refresh, [tripId]);

  async function handleSetBudget(e: FormEvent) {
    e.preventDefault();
    const trip = await api.setTripBudget(tripId, Number(budgetInput));
    setCurrentBudget(trip.budget_amount);
  }

  async function handleAddExpense(e: FormEvent) {
    e.preventDefault();
    await api.createExpense(tripId, { category, description: description || undefined, amount: Number(amount) });
    setDescription("");
    setAmount("");
    refresh();
  }

  const expensesTotal = expenses.reduce((sum, e) => sum + e.amount, 0);
  const confirmedBookingsTotal = bookings
    .filter((b) => b.status === "confirmed" && b.cost != null)
    .reduce((sum, b) => sum + (b.cost ?? 0), 0);
  const committedTotal = expensesTotal + confirmedBookingsTotal;
  const pct = currentBudget ? Math.min(100, Math.round((committedTotal / currentBudget) * 100)) : null;

  const cheapestFlight = cheapestReal(plan?.flights, (f) => f.price_raw);
  const cheapestStay = cheapestReal(plan?.accommodations as { source?: unknown; price_raw?: unknown }[] | undefined, (a) =>
    typeof a.price_raw === "number" ? a.price_raw : null
  );

  return (
    <div className="flex flex-col gap-6">
      {(cheapestFlight || cheapestStay) && (
        <div className="rounded-xl2 border border-ink-900/5 bg-white shadow-card p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Live reference quotes</p>
          <p className="mt-1 text-xs text-ink-500">
            Real prices found while planning — not booked, and not counted in the totals below. Different
            providers' currencies aren't converted or combined.
          </p>
          <div className="mt-3 flex flex-wrap gap-4">
            {cheapestFlight && (
              <div className="rounded-lg bg-surface px-3 py-2 text-sm">
                <span className="font-semibold">
                  {cheapestFlight.price} {cheapestFlight.item.currency}
                </span>{" "}
                <span className="text-ink-500">cheapest live flight ({cheapestFlight.item.airline ?? "unknown airline"})</span>
              </div>
            )}
            {cheapestStay && (
              <div className="rounded-lg bg-surface px-3 py-2 text-sm">
                <span className="font-semibold">
                  {cheapestStay.price} {String((cheapestStay.item as { currency?: unknown }).currency ?? "")}
                </span>{" "}
                <span className="text-ink-500">
                  cheapest live rate/night ({String((cheapestStay.item as { name?: unknown }).name ?? "unknown property")})
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="rounded-xl2 border border-ink-900/5 bg-white shadow-card p-5">
        <form onSubmit={handleSetBudget} className="mb-4 flex items-end gap-3">
          <label className="flex flex-col gap-1 text-xs font-medium">
            Budget target (₹)
            <input
              type="number"
              min={0}
              value={budgetInput}
              onChange={(e) => setBudgetInput(e.target.value)}
              className="w-40 rounded-lg border border-ink-900/10 px-2 py-1.5 text-sm"
            />
          </label>
          <button type="submit" className="rounded-lg border border-ink-900/10 px-3 py-1.5 text-sm font-medium hover:bg-brand-50">
            Set budget
          </button>
        </form>

        {currentBudget != null ? (
          <>
            <div className="h-2.5 w-full overflow-hidden rounded-full bg-ink-900/5">
              <div
                className={`h-full ${committedTotal > currentBudget ? "bg-rose-500" : "bg-brand-500"}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <p className="mt-2 text-sm">
              ₹{committedTotal.toLocaleString()} committed of ₹{currentBudget.toLocaleString()}
              {committedTotal > currentBudget && <span className="ml-2 font-medium text-rose-600">over budget</span>}
            </p>
          </>
        ) : (
          <p className="text-sm text-ink-500">
            ₹{committedTotal.toLocaleString()} committed so far. Set a budget target to track against it.
          </p>
        )}
        <p className="mt-2 text-xs text-ink-500">
          Confirmed bookings: ₹{confirmedBookingsTotal.toLocaleString()} · Logged expenses: ₹
          {expensesTotal.toLocaleString()}. Pending/cancelled bookings and AI-estimated accommodation/dining
          costs aren't included — this is real, user-entered money only, never mixed with an LLM guess.
        </p>
      </div>

      <form onSubmit={handleAddExpense} className="flex flex-wrap items-end gap-3 rounded-xl2 border border-ink-900/5 bg-white shadow-card p-4">
        <label className="flex flex-col gap-1 text-xs font-medium">
          Category
          <select value={category} onChange={(e) => setCategory(e.target.value)} className="rounded-lg border border-ink-900/10 px-2 py-1.5 text-sm">
            {EXPENSE_CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-1 min-w-[180px] flex-col gap-1 text-xs font-medium">
          Description
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g. Beach shack dinner"
            className="rounded-lg border border-ink-900/10 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Amount (₹)
          <input
            type="number"
            min={0}
            required
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="w-28 rounded-lg border border-ink-900/10 px-2 py-1.5 text-sm"
          />
        </label>
        <button type="submit" className="rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-semibold text-white shadow-sm transition-transform hover:-translate-y-0.5 hover:bg-brand-700 active:translate-y-0">
          Add expense
        </button>
      </form>

      {loading && <Spinner />}
      {!loading && expenses.length === 0 && <p className="text-sm text-ink-500">No expenses logged yet.</p>}

      <div className="flex flex-col gap-2">
        {expenses.map((e) => (
          <div key={e.id} className="flex items-center justify-between rounded-xl2 border border-ink-900/5 bg-white shadow-card p-3">
            <div>
              <p className="text-sm font-medium capitalize">{e.category}</p>
              {e.description && <p className="text-xs text-ink-500">{e.description}</p>}
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold">₹{e.amount.toLocaleString()}</span>
              <button onClick={() => api.deleteExpense(tripId, e.id).then(refresh)} className="text-xs text-ink-500 hover:text-rose-600">
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
