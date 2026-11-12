import { NavLink, Outlet } from "react-router-dom";
import OfflineBanner from "./OfflineBanner";
import TopBar from "./TopBar";

interface NavItem {
  label: string;
  to: string;
  icon: string;
}

const travelNav: NavItem[] = [
  { label: "Home", to: "/", icon: "Navigation/home.svg" },
  { label: "Plan a Trip", to: "/plan", icon: "Navigation/plan-trip.svg" },
  { label: "My Trips", to: "/trips", icon: "Navigation/my-trips.svg" },
  { label: "Bookings & Wallet", to: "/bookings", icon: "Navigation/bookings.svg" },
  { label: "Budget & Expenses", to: "/budget", icon: "Navigation/budget.svg" },
  { label: "Group Trips", to: "/group-trips", icon: "Navigation/group-trips.svg" },
  { label: "Travel Companion", to: "/companion", icon: "Navigation/compass.svg" },
];

const aiNav: NavItem[] = [
  { label: "Agent Studio", to: "/ai/agent-studio", icon: "AI-Engineering/agent.svg" },
  { label: "Models & Routing", to: "/ai/models", icon: "AI-Engineering/model.svg" },
  { label: "RAG & Knowledge", to: "/ai/rag", icon: "AI-Engineering/rag.svg" },
  { label: "Workflows", to: "/ai/workflows", icon: "AI-Engineering/workflow.svg" },
  { label: "Observability", to: "/ai/observability", icon: "AI-Engineering/observability.svg" },
  { label: "Evaluations", to: "/ai/evaluations", icon: "AI-Engineering/evaluation.svg" },
  { label: "Security Lab", to: "/ai/security", icon: "AI-Engineering/security.svg" },
];

function NavSection({ title, items }: { title: string; items: NavItem[] }) {
  return (
    <div className="mb-6">
      <p className="px-3 mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">{title}</p>
      <nav className="flex flex-col gap-0.5">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive ? "bg-brand-100 text-brand-700" : "text-ink-700 hover:bg-brand-50"
              }`
            }
          >
            <img src={`/icons/${item.icon}`} alt="" className="h-5 w-5" aria-hidden="true" />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

export default function Layout() {
  return (
    <div className="flex min-h-screen bg-surface">
      <aside className="w-64 shrink-0 border-r border-ink-900/5 bg-white px-3 py-5">
        <div className="mb-6 px-2">
          <div className="flex items-center gap-2">
            <img src="/icons/Logos/voyager-mark.svg" alt="" className="h-7 w-7" aria-hidden="true" />
            <img src="/icons/Logos/voyager-wordmark.svg" alt="Voyager AI" className="h-6" />
          </div>
          <p className="mt-0.5 px-0 text-xs text-ink-500">Travel &amp; AI Engineering Platform</p>
        </div>
        <NavSection title="Travel Workspace" items={travelNav} />
        <NavSection title="AI Engineering Workspace" items={aiNav} />
      </aside>
      <main className="flex-1 overflow-y-auto">
        <OfflineBanner />
        <TopBar />
        <div className="mx-auto max-w-6xl px-8 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
