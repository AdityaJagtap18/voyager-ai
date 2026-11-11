import { useOnlineStatus } from "../hooks/useOnlineStatus";

export default function OfflineBanner() {
  const online = useOnlineStatus();
  if (online) return null;

  return (
    <div className="bg-amber-500 px-4 py-2 text-center text-sm font-medium text-white">
      You're offline — showing the last data loaded. Changes you make now won't save until you're back online.
    </div>
  );
}
