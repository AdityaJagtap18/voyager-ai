import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

export default function TopBar({ onMenuClick }: { onMenuClick: () => void }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [notifOpen, setNotifOpen] = useState(false);

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    navigate(`/plan?destination=${encodeURIComponent(trimmed)}`);
  }

  return (
    <div className="flex items-center gap-2 border-b border-ink-900/5 bg-white px-4 py-3 sm:gap-4 sm:px-8">
      <button
        type="button"
        onClick={onMenuClick}
        aria-label="Toggle navigation"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-ink-700 hover:bg-surface lg:hidden"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
          <path d="M3 6h18M3 12h18M3 18h18" />
        </svg>
      </button>
      <form onSubmit={handleSearch} className="min-w-0 flex-1 sm:max-w-xl">
        <div className="flex items-center gap-2 rounded-lg border border-ink-900/10 bg-surface px-3 py-2">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#5C6680" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='Ask Voyager anything… (e.g., "Plan a 5-day trip to Bali")'
            className="w-full bg-transparent text-sm text-ink-900 outline-none placeholder:text-ink-500"
          />
        </div>
      </form>

      <div className="relative ml-auto flex items-center gap-3">
        <button
          type="button"
          onClick={() => setNotifOpen((o) => !o)}
          aria-label="Notifications"
          className="flex h-9 w-9 items-center justify-center rounded-full text-ink-700 hover:bg-surface"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
        </button>
        {notifOpen && (
          <div className="absolute right-12 top-11 w-56 rounded-lg border border-ink-900/10 bg-white p-3 text-sm text-ink-500 shadow-lg">
            No new notifications yet.
          </div>
        )}
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 text-brand-700">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M20 21a8 8 0 1 0-16 0" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        </span>
      </div>
    </div>
  );
}
