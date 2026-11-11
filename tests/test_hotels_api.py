import pytest

from services import hotels_api


class FakeResponse:
    def __init__(self, status_code, payload, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or str(payload)

    def json(self):
        return self._payload


def test_is_configured_reflects_key_presence(monkeypatch):
    monkeypatch.setattr(hotels_api, "RAPIDAPI_KEY", None)
    assert hotels_api.is_configured() is False
    monkeypatch.setattr(hotels_api, "RAPIDAPI_KEY", "key")
    assert hotels_api.is_configured() is True


def test_search_destination_requires_api_key(monkeypatch):
    monkeypatch.setattr(hotels_api, "RAPIDAPI_KEY", None)
    with pytest.raises(hotels_api.HotelsAPIError):
        hotels_api.search_destination("Goa")


def test_search_destination_parses_entries(monkeypatch):
    monkeypatch.setattr(hotels_api, "RAPIDAPI_KEY", "test-key")
    payload = {
        "data": [
            {
                "dest_id": "-2114039",
                "search_type": "CITY",
                "label": "Goa, Goa State, India",
                "country": "India",
                "latitude": 15.2993,
                "longitude": 74.124,
            }
        ],
        "status": True,
    }
    monkeypatch.setattr(hotels_api.requests, "get", lambda *a, **k: FakeResponse(200, payload))

    results = hotels_api.search_destination("Goa")
    assert results == [
        {
            "dest_id": "-2114039",
            "search_type": "CITY",
            "label": "Goa, Goa State, India",
            "country": "India",
            "latitude": 15.2993,
            "longitude": 74.124,
        }
    ]


def test_search_hotels_parses_property_fields_into_offers(monkeypatch):
    monkeypatch.setattr(hotels_api, "RAPIDAPI_KEY", "test-key")
    payload = {
        "data": {
            "hotels": [
                {
                    "hotel_id": 123456,
                    "property": {
                        "name": "Taj Fort Aguada Resort & Spa",
                        "priceBreakdown": {"grossPrice": {"amountRounded": "₹15,000", "value": 15000.0, "currency": "INR"}},
                        "reviewScore": 8.9,
                        "reviewScoreWord": "Excellent",
                        "accuratePropertyClass": 5,
                        "photoUrls": ["https://example.com/photo.jpg"],
                        "latitude": 15.4989,
                        "longitude": 73.7633,
                    },
                }
            ]
        }
    }
    monkeypatch.setattr(hotels_api.requests, "get", lambda *a, **k: FakeResponse(200, payload))

    offers = hotels_api.search_hotels("-2114039", "CITY", "2026-12-10", "2026-12-15", currency="INR")
    assert offers == [
        {
            "hotel_id": 123456,
            "name": "Taj Fort Aguada Resort & Spa",
            "price_formatted": "₹15,000",
            "price_raw": 15000.0,
            "currency": "INR",
            "review_score": 8.9,
            "review_score_word": "Excellent",
            "star_rating": 5,
            "photo_url": "https://example.com/photo.jpg",
            "latitude": 15.4989,
            "longitude": 73.7633,
        }
    ]


def test_search_hotels_handles_missing_photos_and_class(monkeypatch):
    monkeypatch.setattr(hotels_api, "RAPIDAPI_KEY", "test-key")
    payload = {
        "data": {
            "hotels": [
                {
                    "hotel_id": 7,
                    "property": {
                        "name": "Budget Inn",
                        "priceBreakdown": {"grossPrice": {"amountRounded": "$40", "value": 40.0, "currency": "USD"}},
                        "propertyClass": 2,
                    },
                }
            ]
        }
    }
    monkeypatch.setattr(hotels_api.requests, "get", lambda *a, **k: FakeResponse(200, payload))

    offers = hotels_api.search_hotels("1", "CITY", "2026-12-10", "2026-12-15")
    assert offers[0]["photo_url"] is None
    assert offers[0]["star_rating"] == 2


def test_search_hotels_returns_empty_list_when_no_hotels(monkeypatch):
    monkeypatch.setattr(hotels_api, "RAPIDAPI_KEY", "test-key")
    monkeypatch.setattr(hotels_api.requests, "get", lambda *a, **k: FakeResponse(200, {"data": {"hotels": []}}))
    assert hotels_api.search_hotels("1", "CITY", "2026-12-10", "2026-12-15") == []


def test_get_raises_hotels_api_error_on_http_error(monkeypatch):
    monkeypatch.setattr(hotels_api, "RAPIDAPI_KEY", "test-key")
    monkeypatch.setattr(hotels_api.requests, "get", lambda *a, **k: FakeResponse(500, {}, text="Server error"))
    with pytest.raises(hotels_api.HotelsAPIError):
        hotels_api.search_destination("Goa")
