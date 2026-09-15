"""
Unit tests for Hazard-Aware Route Recommendation Engine.
Tests schemas, proximity decay, hazard penalties, normalized route cost,
route comparisons, validation rules, and OSRM client error handling with mocking.
"""

import unittest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

from backend.schemas.routing import (
    Coordinates,
    GeoJSONLineString,
    RouteHazardDetail,
    RouteItem,
    RouteRecommendationResponse,
    RouteRequest,
)
from backend.services.hazard_analyzer import (
    calculate_hazard_penalty,
    calculate_proximity_factor,
    compute_normalized_costs_and_rank,
    evaluate_single_route,
    generate_recommendation_reason,
)
from backend.services.routing import (
    OSRMError,
    OSRMNoRouteFoundError,
    OSRMRoute,
    OSRMServiceUnavailableError,
    RoutingService,
)


class TestRoutingSchemas(unittest.TestCase):
    """Test validation of Coordinates and RouteRequest schemas."""

    def test_coordinate_validation_valid(self):
        coord = Coordinates(latitude=18.5204, longitude=73.8567)
        self.assertEqual(coord.latitude, 18.5204)
        self.assertEqual(coord.longitude, 73.8567)

    def test_coordinate_validation_invalid_latitude(self):
        with self.assertRaises(ValidationError):
            Coordinates(latitude=95.0, longitude=73.8567)
        with self.assertRaises(ValidationError):
            Coordinates(latitude=-91.0, longitude=73.8567)

    def test_coordinate_validation_invalid_longitude(self):
        with self.assertRaises(ValidationError):
            Coordinates(latitude=18.5204, longitude=185.0)
        with self.assertRaises(ValidationError):
            Coordinates(latitude=18.5204, longitude=-181.0)

    def test_route_request_defaults(self):
        req = RouteRequest(
            origin=Coordinates(latitude=18.5204, longitude=73.8567),
            destination=Coordinates(latitude=18.5310, longitude=73.8470),
        )
        self.assertEqual(req.hazard_radius_meters, 50.0)
        self.assertEqual(req.safety_weight, 0.7)

    def test_invalid_hazard_radius(self):
        # Radius must be between 10.0 and 500.0 meters
        with self.assertRaises(ValidationError):
            RouteRequest(
                origin=Coordinates(latitude=18.52, longitude=73.85),
                destination=Coordinates(latitude=18.53, longitude=73.84),
                hazard_radius_meters=5.0,  # Below 10.0 min
            )
        with self.assertRaises(ValidationError):
            RouteRequest(
                origin=Coordinates(latitude=18.52, longitude=73.85),
                destination=Coordinates(latitude=18.53, longitude=73.84),
                hazard_radius_meters=600.0,  # Above 500.0 max
            )

    def test_invalid_safety_weight(self):
        # Weight must be between 0.0 and 1.0
        with self.assertRaises(ValidationError):
            RouteRequest(
                origin=Coordinates(latitude=18.52, longitude=73.85),
                destination=Coordinates(latitude=18.53, longitude=73.84),
                safety_weight=-0.1,  # Below 0.0 min
            )
        with self.assertRaises(ValidationError):
            RouteRequest(
                origin=Coordinates(latitude=18.52, longitude=73.85),
                destination=Coordinates(latitude=18.53, longitude=73.84),
                safety_weight=1.5,  # Above 1.0 max
            )


class TestProximityAndPenalty(unittest.TestCase):
    """Test proximity factor and individual hazard penalty formulas."""

    def test_proximity_factor_on_route(self):
        # Distance = 0 m -> factor = 1.0
        factor = calculate_proximity_factor(distance=0.0, radius=50.0)
        self.assertEqual(factor, 1.0)

    def test_proximity_factor_at_boundary(self):
        # Distance = radius -> factor = 0.0
        factor = calculate_proximity_factor(distance=50.0, radius=50.0)
        self.assertEqual(factor, 0.0)

    def test_proximity_factor_beyond_boundary(self):
        # Distance > radius -> factor = 0.0
        factor = calculate_proximity_factor(distance=75.0, radius=50.0)
        self.assertEqual(factor, 0.0)

    def test_proximity_factor_linear_decay(self):
        # Distance = 25 m, radius = 50 m -> 1 - 25/50 = 0.5
        factor = calculate_proximity_factor(distance=25.0, radius=50.0)
        self.assertAlmostEqual(factor, 0.5, places=3)

    def test_proximity_factor_zero_radius(self):
        factor = calculate_proximity_factor(distance=10.0, radius=0.0)
        self.assertEqual(factor, 0.0)

    def test_hazard_penalty_full(self):
        # Priority 90.0, proximity 1.0 -> penalty = (90 / 100) * 1.0 = 0.90
        penalty = calculate_hazard_penalty(priority_score=90.0, proximity_factor=1.0)
        self.assertEqual(penalty, 0.9)

    def test_hazard_penalty_decayed(self):
        # Priority 80.0, proximity 0.5 -> penalty = (80 / 100) * 0.5 = 0.40
        penalty = calculate_hazard_penalty(priority_score=80.0, proximity_factor=0.5)
        self.assertEqual(penalty, 0.4)

    def test_hazard_penalty_zero_proximity(self):
        penalty = calculate_hazard_penalty(priority_score=95.0, proximity_factor=0.0)
        self.assertEqual(penalty, 0.0)


class TestRouteEvaluationAndCost(unittest.TestCase):
    """Test candidate route risk calculation, cost normalization, and recommendation ranking."""

    def setUp(self):
        self.sample_geom = {
            "type": "LineString",
            "coordinates": [[73.8567, 18.5204], [73.8470, 18.5310]],
        }

    def test_zero_hazard_route_evaluation(self):
        osrm_r = OSRMRoute(
            distance_meters=5000.0,
            duration_seconds=600.0,
            geometry=self.sample_geom,
        )
        evaluated = evaluate_single_route(
            route_id=1,
            osrm_route=osrm_r,
            hazards=[],
            radius_meters=50.0,
        )
        self.assertEqual(evaluated["hazard_count"], 0)
        self.assertEqual(evaluated["critical_hazard_count"], 0)
        self.assertEqual(evaluated["high_priority_hazard_count"], 0)
        self.assertEqual(evaluated["hazard_risk_score"], 0.0)
        self.assertEqual(evaluated["distance_km"], 5.0)

    def test_shortest_route_wins_when_no_hazards(self):
        """When candidate routes have zero hazards, the shortest route must naturally win."""
        route1 = {
            "route_id": 1,
            "distance_meters": 4000.0,
            "distance_km": 4.0,
            "duration_minutes": 8.0,
            "hazard_count": 0,
            "critical_hazard_count": 0,
            "high_priority_hazard_count": 0,
            "hazard_risk_score": 0.0,
            "geometry": self.sample_geom,
            "hazards": [],
        }
        route2 = {
            "route_id": 2,
            "distance_meters": 6000.0,
            "distance_km": 6.0,
            "duration_minutes": 11.0,
            "hazard_count": 0,
            "critical_hazard_count": 0,
            "high_priority_hazard_count": 0,
            "hazard_risk_score": 0.0,
            "geometry": self.sample_geom,
            "hazards": [],
        }

        ranked, reason = compute_normalized_costs_and_rank([route1, route2], safety_weight=0.7)
        rec = next(r for r in ranked if r.is_recommended)

        self.assertEqual(rec.route_id, 1)
        # Route 1 cost: 4000 / 6000 = 0.667
        # Route 2 cost: 6000 / 6000 = 1.000
        self.assertLess(ranked[0].route_cost, ranked[1].route_cost)
        self.assertIn("shortest available route because no stored hazards were found", reason)

    def test_safer_route_wins_when_hazard_risk_significantly_higher(self):
        """A slightly longer route with zero/low hazards should beat a hazardous shorter route."""
        # Route 1: 5.0 km (shorter), but 3 critical potholes (high risk score 2.7)
        route1 = {
            "route_id": 1,
            "distance_meters": 5000.0,
            "distance_km": 5.0,
            "duration_minutes": 10.0,
            "hazard_count": 3,
            "critical_hazard_count": 3,
            "high_priority_hazard_count": 0,
            "hazard_risk_score": 2.7,
            "geometry": self.sample_geom,
            "hazards": [
                RouteHazardDetail(
                    id=1,
                    hazard_type="pothole",
                    severity="High",
                    priority_score=90.0,
                    priority_level="Critical",
                    confidence=0.9,
                    latitude=18.521,
                    longitude=73.856,
                    distance_from_route=2.0,
                )
            ],
        }
        # Route 2: 5.5 km (+10% longer), 0 hazards (hazard risk score 0.0)
        route2 = {
            "route_id": 2,
            "distance_meters": 5500.0,
            "distance_km": 5.5,
            "duration_minutes": 11.5,
            "hazard_count": 0,
            "critical_hazard_count": 0,
            "high_priority_hazard_count": 0,
            "hazard_risk_score": 0.0,
            "geometry": self.sample_geom,
            "hazards": [],
        }

        # safety_weight = 0.7:
        # Route 1: dist_comp = 5000 / 5500 = 0.909, haz_comp = 2.7 / 2.7 = 1.0 -> cost = 0.909 + 0.7 * 1.0 = 1.609
        # Route 2: dist_comp = 5500 / 5500 = 1.000, haz_comp = 0.0 / 2.7 = 0.0 -> cost = 1.000 + 0.7 * 0.0 = 1.000
        # Route 2 cost (1.000) < Route 1 cost (1.609) -> Route 2 MUST win!
        ranked, reason = compute_normalized_costs_and_rank([route1, route2], safety_weight=0.7)
        rec = next(r for r in ranked if r.is_recommended)

        self.assertEqual(rec.route_id, 2)
        self.assertTrue(rec.is_recommended)
        self.assertIn("Critical priority hazard(s)", reason)

    def test_single_candidate_route(self):
        """Single candidate route returned by OSRM evaluates correctly and is marked recommended."""
        route1 = {
            "route_id": 1,
            "distance_meters": 3500.0,
            "distance_km": 3.5,
            "duration_minutes": 7.0,
            "hazard_count": 1,
            "critical_hazard_count": 0,
            "high_priority_hazard_count": 1,
            "hazard_risk_score": 0.6,
            "geometry": self.sample_geom,
            "hazards": [],
        }
        ranked, reason = compute_normalized_costs_and_rank([route1], safety_weight=0.7)
        self.assertEqual(len(ranked), 1)
        self.assertTrue(ranked[0].is_recommended)
        self.assertIn("only available drivable route", reason)


class TestOSRMServiceMocked(unittest.TestCase):
    """Test OSRM client behavior and error handling using mocked HTTP responses."""

    @patch("httpx.Client.get")
    def test_osrm_successful_routes(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": "Ok",
            "routes": [
                {
                    "distance": 4500.0,
                    "duration": 540.0,
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[73.856, 18.520], [73.847, 18.531]],
                    },
                },
                {
                    "distance": 4800.0,
                    "duration": 580.0,
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[73.856, 18.520], [73.850, 18.525], [73.847, 18.531]],
                    },
                },
            ],
        }
        mock_get.return_value = mock_response

        service = RoutingService(base_url="https://router.project-osrm.org")
        routes = service.get_candidate_routes(73.856, 18.520, 73.847, 18.531)

        self.assertEqual(len(routes), 2)
        self.assertEqual(routes[0].distance_meters, 4500.0)
        self.assertEqual(routes[1].duration_seconds, 580.0)

    @patch("httpx.Client.get")
    def test_osrm_no_route_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": "NoRoute",
            "message": "No route found between points",
        }
        mock_get.return_value = mock_response

        service = RoutingService()
        with self.assertRaises(OSRMNoRouteFoundError):
            service.get_candidate_routes(73.856, 18.520, 73.847, 18.531)

    @patch("httpx.Client.get")
    def test_osrm_service_error_status(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"
        mock_get.return_value = mock_response

        service = RoutingService()
        with self.assertRaises(OSRMServiceUnavailableError):
            service.get_candidate_routes(73.856, 18.520, 73.847, 18.531)

    @patch("httpx.Client.get")
    def test_osrm_network_exception(self, mock_get):
        import httpx
        mock_get.side_effect = httpx.ConnectTimeout("Connection timed out")

        service = RoutingService()
        with self.assertRaises(OSRMServiceUnavailableError):
            service.get_candidate_routes(73.856, 18.520, 73.847, 18.531)


if __name__ == "__main__":
    unittest.main()
