import { FormEvent, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import PageHeader from "../components/PageHeader";
import Spinner from "../components/Spinner";
import type { CurrencyConversion } from "../types";

const COMMON_CURRENCIES = ["USD", "EUR", "GBP", "INR", "JPY", "AUD", "CAD", "CHF", "CNY", "SGD"];

export default function CurrencyConverter() {
  const [amount, setAmount] = useState("100");
  const [from, setFrom] = useState("USD");
  const [to, setTo] = useState("INR");
  const [result, setResult] = useState<CurrencyConversion | null>(null);
  const [availableCurrencies, setAvailableCurrencies] = useState<string[]>(COMMON_CURRENCIES);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .currencyRates("USD")
      .then((r) => setAvailableCurrencies([r.base, ...Object.keys(r.rates)].sort()))
      .catch(() => setAvailableCurrencies(COMMON_CURRENCIES));
  }, []);

  async function handleConvert(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      setResult(await api.convertCurrency(Number(amount), from, to));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Something went wrong. Is the backend running?"
      );
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHeader
        icon="Travel/currency.svg"
        title="Currency Converter"
        description="Real, live exchange rates (ECB reference rates via Frankfurter, no API key required) — never an estimated or hardcoded rate."
      />

      <form
        onSubmit={handleConvert}
        className="flex flex-wrap items-end gap-3 rounded-xl2 border border-ink-900/5 bg-white shadow-card p-6"
      >
        <label className="flex flex-col gap-1 text-sm font-medium">
          Amount
          <input
            type="number"
            min={0}
            step="0.01"
            required
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="w-32 rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          From
          <select
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            {availableCurrencies.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={() => {
            setFrom(to);
            setTo(from);
          }}
          aria-label="Swap currencies"
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-ink-900/10 text-ink-500 hover:bg-surface"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M7 16V4M7 4 3 8M7 4l4 4" />
            <path d="M17 8v12M17 20l4-4M17 20l-4-4" />
          </svg>
        </button>
        <label className="flex flex-col gap-1 text-sm font-medium">
          To
          <select
            value={to}
            onChange={(e) => setTo(e.target.value)}
            className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            {availableCurrencies.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-transform hover:-translate-y-0.5 hover:bg-brand-700 active:translate-y-0 disabled:opacity-50"
        >
          {loading ? "Converting…" : "Convert"}
        </button>
      </form>

      {loading && <div className="mt-6"><Spinner /></div>}
      {error && <p className="mt-4 text-sm text-rose-600">{error}</p>}

      {result && !loading && (
        <div className="mt-6 rounded-xl2 border border-ink-900/5 bg-white shadow-card p-6">
          <p className="text-3xl font-bold text-ink-900">
            {result.converted.toLocaleString()} {result.to}
          </p>
          <p className="mt-1 text-sm text-ink-500">
            {result.amount.toLocaleString()} {result.from} · 1 {result.from} = {result.rate} {result.to}
            {result.date && <> · rates as of {result.date}</>}
          </p>
          <span className="mt-3 inline-block rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
            Live rate
          </span>
        </div>
      )}
    </div>
  );
}
