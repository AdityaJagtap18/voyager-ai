import { FormEvent, useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { api, ApiError } from "../api/client";
import PageHeader from "../components/PageHeader";
import type { MapPlace, MapRoute } from "../types";

function PlacePicker({
  label,
  placeholder,
  value,
  onChange,
}: {
  label: string;
  placeholder: string;
  value: MapPlace | null;
  onChange: (place: MapPlace | null) => void;
}) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<MapPlace[]>([]);

  async function handleQueryChange(q: string) {
    setQuery(q);
    onChange(null);
    if (q.length < 2) {
      setSuggestions([]);
      return;
    }
    try {
      setSuggestions(await api.mapsSearch(q));
    } catch {
      setSuggestions([]);
    }
  }

  return (
    <label className="relative flex flex-1 min-w-[220px] flex-col gap-1 text-sm font-medium">
      {label}
      <input
        required
        value={value ? value.label ?? `${value.lat.toFixed(4)}, ${value.lng.toFixed(4)}` : query}
        onChange={(e) => handleQueryChange(e.target.value)}
        placeholder={placeholder}
        className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
      />
      {!value && suggestions.length > 0 && (
        <div className="absolute top-full z-10 mt-1 w-full rounded-lg border border-ink-900/10 bg-white text-xs shadow-sm">
          {suggestions.map((s, i) => (
            <button
              type="button"
              key={i}
              onClick={() => {
                onChange(s);
                setSuggestions([]);
              }}
              className="block w-full px-3 py-2 text-left hover:bg-ink-900/5"
            >
              {s.label}
            </button>
          ))}
        </div>
      )}
    </label>
  );
}

export default function Maps() {
  const [origin, setOrigin] = useState<MapPlace | null>(null);
  const [destination, setDestination] = useState<MapPlace | null>(null);
  const [route, setRoute] = useState<MapRoute | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mapRef = useRef<HTMLDivElement | null>(null);
  const leafletMap = useRef<L.Map | null>(null);
  const layersRef = useRef<L.Layer[]>([]);

  useEffect(() => {
    if (!mapRef.current || leafletMap.current) return;
    leafletMap.current = L.map(mapRef.current).setView([20, 78], 4);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(leafletMap.current);
  }, []);

  useEffect(() => {
    const map = leafletMap.current;
    if (!map) return;

    layersRef.current.forEach((layer) => map.removeLayer(layer));
    layersRef.current = [];

    const bounds: L.LatLngExpression[] = [];

    if (origin) {
      const marker = L.circleMarker([origin.lat, origin.lng], { color: "#4f46e5", fillOpacity: 1, radius: 7 })
        .addTo(map)
        .bindTooltip(origin.label ?? "Origin");
      layersRef.current.push(marker);
      bounds.push([origin.lat, origin.lng]);
    }
    if (destination) {
      const marker = L.circleMarker([destination.lat, destination.lng], {
        color: "#dc2626",
        fillOpacity: 1,
        radius: 7,
      })
        .addTo(map)
        .bindTooltip(destination.label ?? "Destination");
      layersRef.current.push(marker);
      bounds.push([destination.lat, destination.lng]);
    }
    if (route) {
      const line = L.polyline(route.geometry as L.LatLngExpression[], { color: "#4f46e5", weight: 4 }).addTo(map);
      layersRef.current.push(line);
      bounds.push(...(route.geometry as L.LatLngExpression[]));
    }

    if (bounds.length > 1) {
      map.fitBounds(L.latLngBounds(bounds), { padding: [40, 40] });
    } else if (bounds.length === 1) {
      map.setView(bounds[0], 11);
    }
  }, [origin, destination, route]);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!origin || !destination) {
      setError("Pick an origin and destination from the suggestions.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setRoute(await api.mapsRoute(origin, destination));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHeader
        icon="Travel/map.svg"
        title="Maps"
        description="Real routing (Phase 3), via OpenRouteService — driving distance/duration between two places, drawn on an OpenStreetMap base map."
      />

      <form onSubmit={handleSearch} className="mb-6 flex flex-wrap items-end gap-3 rounded-xl2 border border-ink-900/5 bg-white shadow-card p-6">
        <PlacePicker label="From" placeholder="e.g. Mumbai" value={origin} onChange={setOrigin} />
        <PlacePicker label="To" placeholder="e.g. Goa" value={destination} onChange={setDestination} />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {loading ? "Routing…" : "Get route"}
        </button>
      </form>

      {error && <p className="mb-4 text-sm text-rose-600">{error}</p>}
      {route && (
        <p className="mb-4 text-sm font-medium text-ink-900">
          {route.distance_km} km · {route.duration_h} h driving
        </p>
      )}

      <div ref={mapRef} className="h-[500px] w-full overflow-hidden rounded-xl2 border border-ink-900/5" />
    </div>
  );
}
