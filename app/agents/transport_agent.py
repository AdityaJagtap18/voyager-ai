"""
Transport Agent (Phase 10, transportation discovery slice).

Real, honest scope: this grounds the airport-to-accommodation transfer in an
actual routed distance/duration via OpenRouteService (same provider the
accommodation/itinerary agents already use for geocoding and matrix
distances) - it does NOT invent rental-car listings, taxi fares, or public
transit schedules/prices, because no provider for any of those is
integrated. ORS gives a real route, never a price, so no price is shown;
callers must not synthesize one.
"""
from typing import Dict, Optional, Tuple

from services.ors_api import ORSError, geocode, get_route, is_configured
from utils.logger import logger


class TransportAgent:
    """Finds a real driving transfer from the destination's airport to the trip's accommodation."""

    def find_airport_transfer(
        self, destination: str, accommodation_location: Optional[Tuple[float, float]]
    ) -> Optional[Dict]:
        """
        Returns a real transfer route, or None (never a fabricated one) when:
        - ORS isn't configured
        - there's no accommodation location to route to yet
        - the destination's airport can't be geocoded
        - the routing call fails

        Shape: {"mode": "driving", "from": str, "to": "accommodation",
                "distance_km": float, "duration_h": float, "geometry": [[lat, lng], ...],
                "source": "real"}
        """
        if not is_configured():
            return None
        if not accommodation_location:
            return None

        airport_query = f"{destination} Airport"
        try:
            matches = geocode(airport_query, limit=1)
            if not matches:
                logger.warning(f"Transport: couldn't geocode '{airport_query}', skipping airport transfer")
                return None
            airport_location = matches[0]

            route = get_route(airport_location, accommodation_location, profile="driving-car")
            return {
                "mode": "driving",
                "from": airport_query,
                "to": "accommodation",
                "distance_km": route["distance_km"],
                "duration_h": route["duration_h"],
                "geometry": route["geometry"],
                "source": "real",
            }
        except ORSError as e:
            logger.warning(f"Transport: airport transfer routing failed, skipping: {e}")
            return None
