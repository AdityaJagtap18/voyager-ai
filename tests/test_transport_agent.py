from unittest.mock import patch

from agents.transport_agent import TransportAgent
from services.ors_api import ORSError


def test_find_airport_transfer_returns_none_when_unconfigured():
    agent = TransportAgent()
    with patch("agents.transport_agent.is_configured", return_value=False):
        assert agent.find_airport_transfer("Goa, India", (15.5, 73.8)) is None


def test_find_airport_transfer_returns_none_without_accommodation_location():
    agent = TransportAgent()
    with patch("agents.transport_agent.is_configured", return_value=True):
        assert agent.find_airport_transfer("Goa, India", None) is None


def test_find_airport_transfer_returns_none_when_airport_unresolvable():
    agent = TransportAgent()
    with patch("agents.transport_agent.is_configured", return_value=True), patch(
        "agents.transport_agent.geocode", return_value=[]
    ):
        assert agent.find_airport_transfer("Goa, India", (15.5, 73.8)) is None


def test_find_airport_transfer_returns_real_route():
    agent = TransportAgent()
    with patch("agents.transport_agent.is_configured", return_value=True), patch(
        "agents.transport_agent.geocode", return_value=[(15.38, 73.83)]
    ), patch(
        "agents.transport_agent.get_route",
        return_value={"distance_km": 4.2, "duration_h": 0.15, "geometry": [[15.38, 73.83], [15.5, 73.8]]},
    ) as mock_get_route:
        result = agent.find_airport_transfer("Goa, India", (15.5, 73.8))

    mock_get_route.assert_called_once_with((15.38, 73.83), (15.5, 73.8), profile="driving-car")
    assert result == {
        "mode": "driving",
        "from": "Goa, India Airport",
        "to": "accommodation",
        "distance_km": 4.2,
        "duration_h": 0.15,
        "geometry": [[15.38, 73.83], [15.5, 73.8]],
        "source": "real",
    }


def test_find_airport_transfer_returns_none_on_routing_error():
    agent = TransportAgent()
    with patch("agents.transport_agent.is_configured", return_value=True), patch(
        "agents.transport_agent.geocode", return_value=[(15.38, 73.83)]
    ), patch("agents.transport_agent.get_route", side_effect=ORSError("boom")):
        assert agent.find_airport_transfer("Goa, India", (15.5, 73.8)) is None
