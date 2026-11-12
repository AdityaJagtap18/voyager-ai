import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { api } from "../api/client";
import type { DayActivity, MapPlace } from "../types";

/**
 * Real-route map for one itinerary day, reusing the same OpenRouteService
 * routing (api.mapsRoute) the standalone Maps page already uses. Only plots
 * activities that were actually geocoded by the backend - never invents a
 * pin or a route leg for one that wasn't.
 */
export default function DayMap({ activities }: { activities: DayActivity[] }) {
  const mapRef = useRef<HTMLDivElement | null>(null);
  const leafletMap = useRef<L.Map | null>(null);
  const layersRef = useRef<L.Layer[]>([]);
  const [routeStats, setRouteStats] = useState<{ distanceKm: number; durationH: number } | null>(null);
  const [routeError, setRouteError] = useState(false);

  const stops: { place: MapPlace; activity: DayActivity }[] = activities
    .filter((a) => a.coordinates)
    .map((a) => ({
      place: { label: a.name, lat: a.coordinates!.lat, lng: a.coordinates!.lng },
      activity: a,
    }));

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

    let cancelled = false;
    layersRef.current.forEach((layer) => map.removeLayer(layer));
    layersRef.current = [];
    setRouteStats(null);
    setRouteError(false);

    const bounds: L.LatLngExpression[] = [];
    stops.forEach(({ place, activity }, i) => {
      const marker = L.marker([place.lat, place.lng], {
        icon: L.divIcon({
          className: "",
          html: `<div style="background:#4f46e5;color:white;width:22px;height:22px;border-radius:9999px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;box-shadow:0 1px 3px rgba(0,0,0,0.3)">${i + 1}</div>`,
          iconSize: [22, 22],
          iconAnchor: [11, 11],
        }),
      })
        .addTo(map)
        .bindTooltip(`${i + 1}. ${activity.name}`);
      layersRef.current.push(marker);
      bounds.push([place.lat, place.lng]);
    });

    if (bounds.length > 1) {
      map.fitBounds(L.latLngBounds(bounds), { padding: [30, 30] });
    } else if (bounds.length === 1) {
      map.setView(bounds[0], 13);
    }

    if (stops.length >= 2) {
      Promise.all(
        stops.slice(0, -1).map((stop, i) => api.mapsRoute(stop.place, stops[i + 1].place).catch(() => null))
      ).then((routes) => {
        if (cancelled) return;
        const valid = routes.filter((r): r is NonNullable<typeof r> => r !== null);
        if (valid.length === 0) {
          setRouteError(true);
          return;
        }
        let totalKm = 0;
        let totalH = 0;
        valid.forEach((route) => {
          const line = L.polyline(route.geometry as L.LatLngExpression[], { color: "#4f46e5", weight: 4 }).addTo(
            map
          );
          layersRef.current.push(line);
          totalKm += route.distance_km;
          totalH += route.duration_h;
        });
        if (valid.length < routes.length) setRouteError(true);
        setRouteStats({ distanceKm: Math.round(totalKm * 10) / 10, durationH: totalH });
      });
    }

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activities.map((a) => `${a.name}:${a.coordinates?.lat},${a.coordinates?.lng}`).join("|")]);

  if (stops.length === 0) {
    return (
      <div className="flex h-[280px] items-center justify-center rounded-xl2 border border-ink-900/5 bg-ink-50 text-xs text-ink-400">
        No map data for this day — none of today's stops were geocoded.
      </div>
    );
  }

  return (
    <div>
      <div ref={mapRef} className="h-[280px] w-full overflow-hidden rounded-xl2 border border-ink-900/5" />
      <div className="mt-2 flex items-center justify-between text-xs text-ink-500">
        <span>
          {stops.length} stop{stops.length === 1 ? "" : "s"} plotted
          {stops.length < activities.length && ` (${activities.length - stops.length} not geocoded)`}
        </span>
        {routeStats && (
          <span className="font-medium text-ink-700">
            {routeStats.distanceKm} km · {Math.round(routeStats.durationH * 60)} min total
            {routeError && " (partial)"}
          </span>
        )}
      </div>
    </div>
  );
}
