import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
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
  // Hidden from the sidebar for now (route/page kept intact, just not linked here).
  // { label: "Group Trips", to: "/group-trips", icon: "Navigation/group-trips.svg" },
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

function NavSection({ title, items, onNavigate }: { title: string; items: NavItem[]; onNavigate: () => void }) {
  return (
    <div className="mb-6">
      <p className="px-3 mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">{title}</p>
      <nav className="flex flex-col gap-0.5">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onNavigate}
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
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  // A phone-width viewport has no room for a persistent sidebar, so it's an
  // off-canvas drawer there instead - close it whenever the route changes.
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen bg-surface">
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-ink-900/30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 shrink-0 transform overflow-y-auto border-r border-ink-900/5 bg-white px-3 py-5 transition-transform duration-200 lg:static lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-6 px-2">
          <div className="flex items-center gap-2">
            <img src="/icons/Logos/voyager-mark.svg" alt="" className="h-7 w-7" aria-hidden="true" />
            <img src="/icons/Logos/voyager-wordmark.svg" alt="Voyager AI" className="h-6" />
          </div>
          <p className="mt-0.5 px-0 text-xs text-ink-500">Travel &amp; AI Engineering Platform</p>
        </div>
        <NavSection title="Travel Workspace" items={travelNav} onNavigate={() => setSidebarOpen(false)} />
        <NavSection title="AI Engineering Workspace" items={aiNav} onNavigate={() => setSidebarOpen(false)} />
      </aside>

      <main className="min-w-0 flex-1 overflow-y-auto">
        <OfflineBanner />
        <TopBar onMenuClick={() => setSidebarOpen((o) => !o)} />
        <div className="mx-auto max-w-6xl px-4 py-6 sm:px-8 sm:py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
