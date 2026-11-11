import { useState } from "react";
import { api, ApiError } from "../api/client";

export default function TripShare({ tripId, initialToken }: { tripId: string; initialToken: string | null }) {
  const [token, setToken] = useState<string | null>(initialToken);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const shareUrl = token ? `${window.location.origin}/shared/${token}` : null;

  async function handleCreate() {
    setBusy(true);
    setError(null);
    try {
      const r = await api.createShareLink(tripId);
      setToken(r.share_token);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not create a share link.");
    } finally {
      setBusy(false);
    }
  }

  async function handleRevoke() {
    setBusy(true);
    setError(null);
    try {
      await api.revokeShareLink(tripId);
      setToken(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not revoke the share link.");
    } finally {
      setBusy(false);
    }
  }

  async function handleCopy() {
    if (!shareUrl) return;
    await navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="rounded-xl2 border border-ink-900/5 bg-white p-4">
      <p className="mb-1 text-sm font-medium text-ink-900">Share with travel companions</p>
      <p className="mb-3 text-xs text-ink-500">
        Anyone with the link can view this trip's itinerary, restaurants, and accommodations — read-only, no
        account needed. Bookings, budget, and documents stay private.
      </p>
      {error && <p className="mb-2 text-sm text-rose-600">{error}</p>}
      {!token && (
        <button
          onClick={handleCreate}
          disabled={busy}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {busy ? "Creating…" : "Create share link"}
        </button>
      )}
      {token && (
        <div className="flex flex-wrap items-center gap-2">
          <code className="rounded-lg bg-ink-900/5 px-3 py-2 text-xs text-ink-900">{shareUrl}</code>
          <button onClick={handleCopy} className="text-sm font-medium text-brand-600">
            {copied ? "Copied!" : "Copy"}
          </button>
          <button onClick={handleRevoke} disabled={busy} className="text-sm text-ink-500 hover:text-rose-600">
            Revoke
          </button>
        </div>
      )}
    </div>
  );
}
