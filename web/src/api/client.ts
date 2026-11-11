import type {
  Booking,
  BookingCreateRequest,
  ModelInfo,
  TripCreateRequest,
  TripDetail,
  TripExpense,
  TripSummary,
  ExpenseCreateRequest,
} from "../types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? `Request failed: ${res.status}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; config_valid: boolean }>("/api/health"),
  listModels: () => request<ModelInfo[]>("/api/models"),
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
};
