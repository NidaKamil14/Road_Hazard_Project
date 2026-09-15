"""
OSRM Routing Service Client.
Communicates with the Open Source Routing Machine (OSRM) driving API to obtain candidate routes.
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, List
import httpx


class OSRMError(Exception):
    """Base exception for OSRM routing errors."""
    pass


class OSRMServiceUnavailableError(OSRMError):
    """Raised when the OSRM service cannot be reached or times out."""
    pass


class OSRMNoRouteFoundError(OSRMError):
    """Raised when no drivable route exists between coordinates."""
    pass


@dataclass
class OSRMRoute:
    """Internal representation of a candidate route returned by OSRM."""
    distance_meters: float
    duration_seconds: float
    geometry: Dict[str, Any]  # GeoJSON LineString dictionary


class RoutingService:
    """HTTP client for OSRM driving service."""

    def __init__(self, base_url: str = None, timeout_seconds: float = 10.0):
        self.base_url = (base_url or os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")).rstrip("/")
        self.timeout_seconds = timeout_seconds

    def get_candidate_routes(
        self,
        origin_lon: float,
        origin_lat: float,
        destination_lon: float,
        destination_lat: float,
    ) -> List[OSRMRoute]:
        """Fetch candidate driving routes between origin and destination coordinates.

        OSRM coordinate order is strictly {longitude},{latitude}.
        """
        url = (
            f"{self.base_url}/route/v1/driving/"
            f"{origin_lon:.6f},{origin_lat:.6f};{destination_lon:.6f},{destination_lat:.6f}"
        )
        params = {
            "alternatives": "true",
            "overview": "full",
            "geometries": "geojson",
            "steps": "false",
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(url, params=params)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as err:
            raise OSRMServiceUnavailableError(
                f"Routing service is temporarily unavailable or timed out: {err}"
            ) from err
        except Exception as err:
            raise OSRMServiceUnavailableError(f"Failed to connect to routing service: {err}") from err

        if response.status_code != 200:
            raise OSRMServiceUnavailableError(
                f"Routing service returned HTTP {response.status_code}: {response.text}"
            )

        try:
            data = response.json()
        except Exception as err:
            raise OSRMError(f"Malformed JSON response from routing service: {err}") from err

        code = data.get("code")
        if code == "NoRoute":
            raise OSRMNoRouteFoundError("No drivable route was found between the selected locations.")
        elif code != "Ok":
            msg = data.get("message", "Unknown error")
            raise OSRMError(f"Routing service error ({code}): {msg}")

        routes_data = data.get("routes", [])
        if not routes_data:
            raise OSRMNoRouteFoundError("No drivable route was found between the selected locations.")

        candidate_routes: List[OSRMRoute] = []
        for r in routes_data:
            dist = float(r.get("distance", 0.0))
            dur = float(r.get("duration", 0.0))
            geom = r.get("geometry", {})
            if not geom or geom.get("type") != "LineString":
                continue
            candidate_routes.append(
                OSRMRoute(
                    distance_meters=dist,
                    duration_seconds=dur,
                    geometry=geom,
                )
            )

        if not candidate_routes:
            raise OSRMNoRouteFoundError("No valid LineString geometry route returned by routing service.")

        return candidate_routes
