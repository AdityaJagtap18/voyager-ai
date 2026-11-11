import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import PlanTrip from "./pages/PlanTrip";
import MyTrips from "./pages/MyTrips";
import TripDetail from "./pages/TripDetail";
import TripPickerHub from "./pages/TripPickerHub";
import ComingSoon from "./pages/ComingSoon";
import ModelsRouting from "./pages/ModelsRouting";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/plan" element={<PlanTrip />} />
        <Route path="/trips" element={<MyTrips />} />
        <Route path="/trips/:id" element={<TripDetail />} />

        <Route
          path="/bookings"
          element={
            <TripPickerHub
              title="Bookings & Wallet"
              description="Flight/hotel references, confirmation status and costs, per trip."
              tab="bookings"
            />
          }
        />
        <Route
          path="/budget"
          element={
            <TripPickerHub
              title="Budget & Expenses"
              description="Set a budget target and track spending against it, per trip."
              tab="budget"
            />
          }
        />
        <Route path="/group-trips" element={<ComingSoon title="Group Trips" />} />
        <Route path="/companion" element={<ComingSoon title="Travel Companion" />} />

        <Route path="/ai/agent-studio" element={<ComingSoon title="Agent Studio" />} />
        <Route path="/ai/models" element={<ModelsRouting />} />
        <Route path="/ai/rag" element={<ComingSoon title="RAG & Knowledge" />} />
        <Route path="/ai/workflows" element={<ComingSoon title="Workflows" />} />
        <Route path="/ai/observability" element={<ComingSoon title="Observability" />} />
        <Route path="/ai/evaluations" element={<ComingSoon title="Evaluations" />} />
        <Route path="/ai/security" element={<ComingSoon title="Security Lab" />} />
      </Route>
    </Routes>
  );
}
