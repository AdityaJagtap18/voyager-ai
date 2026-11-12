export default function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <p className="flex items-center gap-2 text-sm text-ink-500">
      <svg
        className="h-4 w-4 animate-spin text-brand-500"
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden="true"
      >
        <circle className="opacity-25" cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" />
        <path className="opacity-90" fill="currentColor" d="M21 12a9 9 0 0 0-9-9V0a12 12 0 0 1 12 12h-3Z" />
      </svg>
      {label}
    </p>
  );
}
