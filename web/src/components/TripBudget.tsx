import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";
import { EXPENSE_CATEGORIES, type TripExpense } from "../types";

export default function TripBudget({ tripId, budgetAmount }: { tripId: string; budgetAmount: number | null }) {
  const [expenses, setExpenses] = useState<TripExpense[]>([]);
  const [loading, setLoading] = useState(true);
  const [budgetInput, setBudgetInput] = useState(budgetAmount?.toString() ?? "");
  const [category, setCategory] = useState<string>(EXPENSE_CATEGORIES[0]);
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [currentBudget, setCurrentBudget] = useState(budgetAmount);

  function refresh() {
    api.listExpenses(tripId).then(setExpenses).finally(() => setLoading(false));
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

  const total = expenses.reduce((sum, e) => sum + e.amount, 0);
  const pct = currentBudget ? Math.min(100, Math.round((total / currentBudget) * 100)) : null;

  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-xl2 border border-ink-900/5 bg-white p-5">
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
                className={`h-full ${total > currentBudget ? "bg-rose-500" : "bg-brand-500"}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <p className="mt-2 text-sm">
              ₹{total.toLocaleString()} spent of ₹{currentBudget.toLocaleString()}
              {total > currentBudget && <span className="ml-2 font-medium text-rose-600">over budget</span>}
            </p>
          </>
        ) : (
          <p className="text-sm text-ink-500">₹{total.toLocaleString()} spent so far. Set a budget target to track against it.</p>
        )}
      </div>

      <form onSubmit={handleAddExpense} className="flex flex-wrap items-end gap-3 rounded-xl2 border border-ink-900/5 bg-white p-4">
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
        <button type="submit" className="rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-brand-700">
          Add expense
        </button>
      </form>

      {loading && <p className="text-sm text-ink-500">Loading…</p>}
      {!loading && expenses.length === 0 && <p className="text-sm text-ink-500">No expenses logged yet.</p>}

      <div className="flex flex-col gap-2">
        {expenses.map((e) => (
          <div key={e.id} className="flex items-center justify-between rounded-xl2 border border-ink-900/5 bg-white p-3">
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
