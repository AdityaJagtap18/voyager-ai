import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import PlanTrip from "./pages/PlanTrip";
import MyTrips from "./pages/MyTrips";
import TripDetail from "./pages/TripDetail";
import TripPickerHub from "./pages/TripPickerHub";
import ComingSoon from "./pages/ComingSoon";
import ModelsRouting from "./pages/ModelsRouting";
import AgentStudio from "./pages/AgentStudio";
import RagKnowledge from "./pages/RagKnowledge";
import Observability from "./pages/Observability";
import Evaluations from "./pages/Evaluations";
import SecurityLab from "./pages/SecurityLab";
import SharedTrip from "./pages/SharedTrip";
import Flights from "./pages/Flights";
import Hotels from "./pages/Hotels";
import Weather from "./pages/Weather";
import Maps from "./pages/Maps";
import CurrencyConverter from "./pages/CurrencyConverter";

export default function App() {
  return (
    <Routes>
      <Route path="/shared/:token" element={<SharedTrip />} />
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
              icon="Navigation/bookings.svg"
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
              icon="Navigation/budget.svg"
            />
          }
        />
        <Route path="/flights" element={<Flights />} />
        <Route path="/hotels" element={<Hotels />} />
        <Route path="/weather" element={<Weather />} />
        <Route path="/maps" element={<Maps />} />
        <Route path="/currency" element={<CurrencyConverter />} />
        <Route path="/group-trips" element={<ComingSoon title="Group Trips" />} />
        <Route path="/companion" element={<ComingSoon title="Travel Companion" />} />

        <Route path="/ai/agent-studio" element={<AgentStudio />} />
        <Route path="/ai/models" element={<ModelsRouting />} />
        <Route path="/ai/rag" element={<RagKnowledge />} />
        <Route path="/ai/workflows" element={<ComingSoon title="Workflows" />} />
        <Route path="/ai/observability" element={<Observability />} />
        <Route path="/ai/evaluations" element={<Evaluations />} />
        <Route path="/ai/security" element={<SecurityLab />} />
      </Route>
    </Routes>
  );
}
