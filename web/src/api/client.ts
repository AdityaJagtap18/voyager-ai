import type {
  AgentInfo,
  Booking,
  BookingCreateRequest,
  EvaluationRunDetail,
  EvaluationRunRequest,
  EvaluationRunSummary,
  FlightOffer,
  FrameworkInfo,
  GuardrailEventSummary,
  GuardrailScanResult,
  HotelOffer,
  KnowledgeDocumentCreateRequest,
  KnowledgeDocumentSummary,
  KnowledgeSearchResult,
  MapPlace,
  MapRoute,
  ModelInfo,
  PlaceSuggestion,
  PublicTripView,
  ShareLinkResponse,
  TripCreateRequest,
  TripDetail,
  TripDocumentSummary,
  TripExpense,
  TripSummary,
  ExpenseCreateRequest,
  WeatherForecast,
} from "../types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// Offline support (Phase 4, remaining scope): cache every successful GET's
// JSON in localStorage, and fall back to that cache if the network request
// itself fails (not an HTTP error — a real connectivity failure, e.g. the
// browser is offline). Lets My Trips / Trip Detail still show the last-known
// data instead of a blank error screen while offline; it's stale-but-present
// data, not a full offline-write queue (there's nothing to sync back once
// reconnected, since nothing was written while offline).
const CACHE_PREFIX = "voyager_cache:";

function cacheGet<T>(path: string): T | null {
  try {
    const raw = localStorage.getItem(CACHE_PREFIX + path);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function cacheSet(path: string, data: unknown) {
  try {
    localStorage.setItem(CACHE_PREFIX + path, JSON.stringify(data));
  } catch {
    // localStorage unavailable/full — caching is a convenience, never fatal.
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isGet = !init?.method || init.method === "GET";

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch (networkError) {
    if (isGet) {
      const cached = cacheGet<T>(path);
      if (cached !== null) return cached;
    }
    throw networkError;
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? `Request failed: ${res.status}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  const data = (await res.json()) as T;
  if (isGet) cacheSet(path, data);
  return data;
}

export const api = {
  health: () => request<{ status: string; config_valid: boolean }>("/api/health"),
  listModels: () => request<ModelInfo[]>("/api/models"),
  listFrameworks: () => request<FrameworkInfo[]>("/api/frameworks"),
  listAgents: () => request<AgentInfo[]>("/api/agents"),
  listTrips: () => request<TripSummary[]>("/api/trips"),
  getTrip: (id: string) => request<TripDetail>(`/api/trips/${id}`),
  createTrip: (payload: TripCreateRequest) =>
    request<TripDetail>("/api/trips", { method: "POST", body: JSON.stringify(payload) }),
  setTripBudget: (id: string, budget_amount: number) =>
    request<TripDetail>(`/api/trips/${id}`, { method: "PATCH", body: JSON.stringify({ budget_amount }) }),

  listBookings: (tripId: string) => request<Booking[]>(`/api/trips/${tripId}/bookings`),
  createBooking: (tripId: string, payload: BookingCreateRequest) =>
    request<Booking>(`/api/trips/${tripId}/bookings`, { method: "POST", body: JSON.stringify(payload) }),
  updateBookingStatus: (tripId: string, bookingId: string, status: string) =>
    request<Booking>(`/api/trips/${tripId}/bookings/${bookingId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  deleteBooking: (tripId: string, bookingId: string) =>
    request<void>(`/api/trips/${tripId}/bookings/${bookingId}`, { method: "DELETE" }),

  listExpenses: (tripId: string) => request<TripExpense[]>(`/api/trips/${tripId}/expenses`),
  createExpense: (tripId: string, payload: ExpenseCreateRequest) =>
    request<TripExpense>(`/api/trips/${tripId}/expenses`, { method: "POST", body: JSON.stringify(payload) }),
  deleteExpense: (tripId: string, expenseId: string) =>
    request<void>(`/api/trips/${tripId}/expenses/${expenseId}`, { method: "DELETE" }),

  listKnowledge: () => request<KnowledgeDocumentSummary[]>("/api/knowledge"),
  createKnowledge: (payload: KnowledgeDocumentCreateRequest) =>
    request<KnowledgeDocumentSummary>("/api/knowledge", { method: "POST", body: JSON.stringify(payload) }),
  searchKnowledge: (query: string, destination?: string, top_k = 5) => {
    const params = new URLSearchParams({ query, top_k: String(top_k) });
    if (destination) params.set("destination", destination);
    return request<KnowledgeSearchResult[]>(`/api/knowledge/search?${params.toString()}`);
  },

  listEvaluationRuns: () => request<EvaluationRunSummary[]>("/api/evaluations"),
  getEvaluationRun: (id: string) => request<EvaluationRunDetail>(`/api/evaluations/${id}`),
  createEvaluationRun: (payload: EvaluationRunRequest) =>
    request<EvaluationRunDetail>("/api/evaluations", { method: "POST", body: JSON.stringify(payload) }),

  scanText: (text: string) =>
    request<GuardrailScanResult>("/api/guardrails/scan", { method: "POST", body: JSON.stringify({ text }) }),
  listGuardrailEvents: () => request<GuardrailEventSummary[]>("/api/guardrails/events"),

  listTripDocuments: (tripId: string) => request<TripDocumentSummary[]>(`/api/trips/${tripId}/documents`),
  uploadTripDocument: async (tripId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${BASE_URL}/api/trips/${tripId}/documents`, { method: "POST", body: formData });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, body.detail ?? `Request failed: ${res.status}`);
    }
    return res.json() as Promise<TripDocumentSummary>;
  },
  tripDocumentDownloadUrl: (tripId: string, documentId: string) =>
    `${BASE_URL}/api/trips/${tripId}/documents/${documentId}/download`,
  deleteTripDocument: (tripId: string, documentId: string) =>
    request<void>(`/api/trips/${tripId}/documents/${documentId}`, { method: "DELETE" }),

  createShareLink: (tripId: string) =>
    request<ShareLinkResponse>(`/api/trips/${tripId}/share`, { method: "POST" }),
  revokeShareLink: (tripId: string) => request<void>(`/api/trips/${tripId}/share`, { method: "DELETE" }),
  getSharedTrip: (shareToken: string) => request<PublicTripView>(`/api/public/trips/${shareToken}`),

  flightsAutocomplete: (query: string) =>
    request<PlaceSuggestion[]>(`/api/flights/autocomplete?${new URLSearchParams({ query })}`),
  flightsSearch: (origin: string, destination: string, departDate: string, currency = "USD") =>
    request<FlightOffer[]>(
      `/api/flights/search?${new URLSearchParams({ origin, destination, depart_date: departDate, currency })}`
    ),

  hotelsAutocomplete: (query: string) =>
    request<PlaceSuggestion[]>(`/api/hotels/autocomplete?${new URLSearchParams({ query })}`),
  hotelsSearch: (
    destId: string,
    searchType: string,
    checkinDate: string,
    checkoutDate: string,
    currency = "USD"
  ) =>
    request<HotelOffer[]>(
      `/api/hotels/search?${new URLSearchParams({
        dest_id: destId,
        search_type: searchType,
        checkin_date: checkinDate,
        checkout_date: checkoutDate,
        currency,
      })}`
    ),

  weatherForecast: (destination: string) =>
    request<WeatherForecast>(`/api/weather/forecast?${new URLSearchParams({ destination })}`),

  mapsSearch: (query: string) =>
    request<MapPlace[]>(`/api/maps/search?${new URLSearchParams({ query })}`),
  mapsRoute: (origin: MapPlace, destination: MapPlace) =>
    request<MapRoute>(
      `/api/maps/route?${new URLSearchParams({
        origin_lat: String(origin.lat),
        origin_lng: String(origin.lng),
        dest_lat: String(destination.lat),
        dest_lng: String(destination.lng),
      })}`
    ),
};
