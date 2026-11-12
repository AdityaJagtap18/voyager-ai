import pytest

from services import sky_scrapper_api


class FakeResponse:
    def __init__(self, status_code, payload, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or str(payload)

    def json(self):
        return self._payload


def test_is_configured_reflects_key_presence(monkeypatch):
    monkeypatch.setattr(sky_scrapper_api, "RAPIDAPI_KEY", None)
    assert sky_scrapper_api.is_configured() is False
    monkeypatch.setattr(sky_scrapper_api, "RAPIDAPI_KEY", "key")
    assert sky_scrapper_api.is_configured() is True


def test_search_airport_requires_api_key(monkeypatch):
    monkeypatch.setattr(sky_scrapper_api, "RAPIDAPI_KEY", None)
    with pytest.raises(sky_scrapper_api.SkyScrapperAPIError):
        sky_scrapper_api.search_airport("Goa")


def test_search_airport_parses_presentation_and_navigation(monkeypatch):
    monkeypatch.setattr(sky_scrapper_api, "RAPIDAPI_KEY", "test-key")
    payload = {
        "data": [
            {
                "presentation": {"title": "Goa"},
                "navigation": {"relevantFlightParams": {"skyId": "IGOI", "entityId": "27541888"}},
            }
        ]
    }
    monkeypatch.setattr(sky_scrapper_api.requests, "get", lambda *a, **k: FakeResponse(200, payload))

    results = sky_scrapper_api.search_airport("Goa")
    assert results == [{"title": "Goa", "sky_id": "IGOI", "entity_id": "27541888"}]


def test_get_raises_error_on_http_error(monkeypatch):
    monkeypatch.setattr(sky_scrapper_api, "RAPIDAPI_KEY", "test-key")
    monkeypatch.setattr(sky_scrapper_api.requests, "get", lambda *a, **k: FakeResponse(403, {}, text="Forbidden"))
    with pytest.raises(sky_scrapper_api.SkyScrapperAPIError):
        sky_scrapper_api.search_airport("Goa")


def test_search_flights_for_trip_returns_none_when_unconfigured(monkeypatch):
    monkeypatch.setattr(sky_scrapper_api, "RAPIDAPI_KEY", None)
    assert sky_scrapper_api.search_flights_for_trip("Mumbai", "Goa", "2026-12-10") is None


def test_search_flights_for_trip_returns_none_when_origin_unresolvable(monkeypatch):
    monkeypatch.setattr(sky_scrapper_api, "RAPIDAPI_KEY", "test-key")
    monkeypatch.setattr(sky_scrapper_api, "search_airport", lambda q: [])
    assert sky_scrapper_api.search_flights_for_trip("Nowhereville", "Goa", "2026-12-10") is None


def test_search_flights_for_trip_returns_none_when_no_offers(monkeypatch):
    monkeypatch.setattr(sky_scrapper_api, "RAPIDAPI_KEY", "test-key")
    monkeypatch.setattr(
        sky_scrapper_api,
        "search_airport",
        lambda q: [{"title": q, "sky_id": "XXX", "entity_id": "1"}],
    )
    monkeypatch.setattr(sky_scrapper_api, "_search_flights", lambda *a, **k: [])
    assert sky_scrapper_api.search_flights_for_trip("Mumbai", "Goa", "2026-12-10") is None


def test_search_flights_for_trip_parses_real_offer(monkeypatch):
    monkeypatch.setattr(sky_scrapper_api, "RAPIDAPI_KEY", "test-key")

    def fake_search_airport(query):
        sky_id = "BOM" if query == "Mumbai" else "GOI"
        return [{"title": query, "sky_id": sky_id, "entity_id": "1"}]

    monkeypatch.setattr(sky_scrapper_api, "search_airport", fake_search_airport)
    payload = {
        "data": {
            "itineraries": [
                {
                    "price": {"formatted": "$120", "raw": 120.0},
                    "legs": [
                        {
                            "durationInMinutes": 135,
                            "stopCount": 0,
                            "origin": {"displayCode": "BOM"},
                            "destination": {"displayCode": "GOI"},
                            "departure": "2026-12-10T17:45:00",
                            "arrival": "2026-12-10T20:00:00",
                            "carriers": {"marketing": [{"name": "IndiGo"}]},
                        }
                    ],
                }
            ]
        }
    }
    monkeypatch.setattr(sky_scrapper_api.requests, "get", lambda *a, **k: FakeResponse(200, payload))

    offers = sky_scrapper_api.search_flights_for_trip("Mumbai", "Goa", "2026-12-10")
    assert offers == [
        {
            "price": "$120",
            "price_raw": 120.0,
            "currency": "USD",
            "airline": "IndiGo",
            "duration_minutes": 135,
            "stops": 0,
            "origin": "BOM",
            "destination": "GOI",
            "departure": "2026-12-10T17:45:00",
            "arrival": "2026-12-10T20:00:00",
            "source": "real",
            "origin_query": "Mumbai",
            "destination_query": "Goa",
        }
    ]


def test_search_flights_for_trip_returns_none_on_provider_error(monkeypatch):
    monkeypatch.setattr(sky_scrapper_api, "RAPIDAPI_KEY", "test-key")

    def raise_error(query):
        raise sky_scrapper_api.SkyScrapperAPIError("boom")

    monkeypatch.setattr(sky_scrapper_api, "search_airport", raise_error)
    assert sky_scrapper_api.search_flights_for_trip("Mumbai", "Goa", "2026-12-10") is None
