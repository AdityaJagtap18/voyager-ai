import pytest

from services import flights_api


class FakeResponse:
    def __init__(self, status_code, payload, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or str(payload)

    def json(self):
        return self._payload


def test_is_configured_reflects_key_presence(monkeypatch):
    monkeypatch.setattr(flights_api, "RAPIDAPI_KEY", None)
    assert flights_api.is_configured() is False
    monkeypatch.setattr(flights_api, "RAPIDAPI_KEY", "key")
    assert flights_api.is_configured() is True


def test_autocomplete_place_requires_api_key(monkeypatch):
    monkeypatch.setattr(flights_api, "RAPIDAPI_KEY", None)
    with pytest.raises(flights_api.FlightsAPIError):
        flights_api.autocomplete_place("Goa")


def test_autocomplete_place_parses_presentation_and_navigation(monkeypatch):
    monkeypatch.setattr(flights_api, "RAPIDAPI_KEY", "test-key")
    payload = {
        "data": [
            {
                "presentation": {"title": "Goa", "subtitle": "India", "skyId": "IGOI"},
                "navigation": {"entityId": "27541888", "entityType": "CITY"},
            }
        ],
        "status": True,
    }
    monkeypatch.setattr(flights_api.requests, "get", lambda *a, **k: FakeResponse(200, payload))

    results = flights_api.autocomplete_place("Goa")
    assert results == [
        {"title": "Goa", "subtitle": "India", "sky_id": "IGOI", "entity_id": "27541888", "type": "CITY"}
    ]


def test_search_one_way_parses_best_bucket_into_offers(monkeypatch):
    monkeypatch.setattr(flights_api, "RAPIDAPI_KEY", "test-key")
    payload = {
        "data": {
            "itineraries": {
                "buckets": [
                    {
                        "id": "Best",
                        "items": [
                            {
                                "price": {"formatted": "₹4,977", "raw": 4977.0},
                                "legs": [
                                    {
                                        "durationInMinutes": 85,
                                        "stopCount": 0,
                                        "origin": {"displayCode": "BOM"},
                                        "destination": {"displayCode": "GOI"},
                                        "departure": "2026-12-10T17:45:00",
                                        "arrival": "2026-12-10T19:10:00",
                                        "carriers": {"marketing": [{"name": "Air India Express"}]},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        }
    }
    monkeypatch.setattr(flights_api.requests, "get", lambda *a, **k: FakeResponse(200, payload))

    offers = flights_api.search_one_way("BOM", "GOI", "2026-12-10", currency="INR")
    assert offers == [
        {
            "price": "₹4,977",
            "price_raw": 4977.0,
            "currency": "INR",
            "airline": "Air India Express",
            "duration_minutes": 85,
            "stops": 0,
            "origin": "BOM",
            "destination": "GOI",
            "departure": "2026-12-10T17:45:00",
            "arrival": "2026-12-10T19:10:00",
        }
    ]


def test_search_one_way_returns_empty_list_when_no_buckets(monkeypatch):
    monkeypatch.setattr(flights_api, "RAPIDAPI_KEY", "test-key")
    monkeypatch.setattr(
        flights_api.requests, "get", lambda *a, **k: FakeResponse(200, {"data": {"itineraries": {"buckets": []}}})
    )
    assert flights_api.search_one_way("BOM", "GOI", "2026-12-10") == []


def test_get_raises_flights_api_error_on_http_error(monkeypatch):
    monkeypatch.setattr(flights_api, "RAPIDAPI_KEY", "test-key")
    monkeypatch.setattr(flights_api.requests, "get", lambda *a, **k: FakeResponse(403, {}, text="Forbidden"))
    with pytest.raises(flights_api.FlightsAPIError):
        flights_api.autocomplete_place("Goa")


def test_search_flights_for_trip_returns_none_when_unconfigured(monkeypatch):
    monkeypatch.setattr(flights_api, "RAPIDAPI_KEY", None)
    assert flights_api.search_flights_for_trip("Mumbai", "Goa", "2026-12-10") is None


def test_search_flights_for_trip_returns_none_when_origin_unresolvable(monkeypatch):
    monkeypatch.setattr(flights_api, "RAPIDAPI_KEY", "test-key")
    monkeypatch.setattr(flights_api, "autocomplete_place", lambda q: [])
    assert flights_api.search_flights_for_trip("Nowhereville", "Goa", "2026-12-10") is None


def test_search_flights_for_trip_returns_none_when_no_offers(monkeypatch):
    monkeypatch.setattr(flights_api, "RAPIDAPI_KEY", "test-key")
    monkeypatch.setattr(
        flights_api,
        "autocomplete_place",
        lambda q: [{"title": q, "subtitle": "", "sky_id": "XXX", "entity_id": "1", "type": "CITY"}],
    )
    monkeypatch.setattr(flights_api, "search_one_way", lambda *a, **k: [])
    assert flights_api.search_flights_for_trip("Mumbai", "Goa", "2026-12-10") is None


def test_search_flights_for_trip_tags_offers_as_real(monkeypatch):
    monkeypatch.setattr(flights_api, "RAPIDAPI_KEY", "test-key")

    def fake_autocomplete(query):
        sky_id = "BOM" if query == "Mumbai" else "GOI"
        return [{"title": query, "subtitle": "India", "sky_id": sky_id, "entity_id": "1", "type": "CITY"}]

    monkeypatch.setattr(flights_api, "autocomplete_place", fake_autocomplete)
    monkeypatch.setattr(
        flights_api,
        "search_one_way",
        lambda origin, destination, depart_date, **k: [
            {"price": "₹4,977", "airline": "Air India Express", "origin": origin, "destination": destination}
        ],
    )

    offers = flights_api.search_flights_for_trip("Mumbai", "Goa", "2026-12-10")
    assert offers == [
        {
            "price": "₹4,977",
            "airline": "Air India Express",
            "origin": "BOM",
            "destination": "GOI",
            "source": "real",
            "origin_query": "Mumbai",
            "destination_query": "Goa",
        }
    ]


def test_search_flights_for_trip_returns_none_on_provider_error(monkeypatch):
    monkeypatch.setattr(flights_api, "RAPIDAPI_KEY", "test-key")

    def raise_error(query):
        raise flights_api.FlightsAPIError("boom")

    monkeypatch.setattr(flights_api, "autocomplete_place", raise_error)
    assert flights_api.search_flights_for_trip("Mumbai", "Goa", "2026-12-10") is None
