import type { TripCreateRequest, TripDetail, TripSummary } from "../types";

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
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; config_valid: boolean }>("/api/health"),
  listTrips: () => request<TripSummary[]>("/api/trips"),
  getTrip: (id: string) => request<TripDetail>(`/api/trips/${id}`),
  createTrip: (payload: TripCreateRequest) =>
    request<TripDetail>("/api/trips", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
