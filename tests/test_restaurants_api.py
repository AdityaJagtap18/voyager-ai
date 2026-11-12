import pytest

from services import restaurants_api


class FakeResponse:
    def __init__(self, status_code, payload, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or str(payload)

    def json(self):
        return self._payload


def test_is_configured_reflects_key_presence(monkeypatch):
    monkeypatch.setattr(restaurants_api, "RAPIDAPI_KEY", None)
    assert restaurants_api.is_configured() is False
    monkeypatch.setattr(restaurants_api, "RAPIDAPI_KEY", "key")
    assert restaurants_api.is_configured() is True


def test_search_restaurants_requires_api_key(monkeypatch):
    monkeypatch.setattr(restaurants_api, "RAPIDAPI_KEY", None)
    with pytest.raises(restaurants_api.RestaurantsAPIError):
        restaurants_api.search_restaurants("Jaipur, India")


def test_search_restaurants_parses_entries(monkeypatch):
    monkeypatch.setattr(restaurants_api, "RAPIDAPI_KEY", "test-key")
    payload = {
        "data": [
            {
                "name": "Govindam Retreat",
                "rating": 4.4,
                "review_count": 9726,
                "price_level": "₹400–600",
                "full_address": "Gangori Bazaar, Jaipur, Rajasthan 302002, India",
                "about": {"summary": "Traditional Rajasthani fare in plush, atmospheric interiors."},
                "type": "Restaurant",
                "subtypes": ["Restaurant", "Breakfast restaurant"],
                "latitude": 26.9288767,
                "longitude": 75.8255344,
                "website": "https://govindamretreat.in",
            }
        ]
    }
    monkeypatch.setattr(restaurants_api.requests, "get", lambda *a, **k: FakeResponse(200, payload))

    results = restaurants_api.search_restaurants("Jaipur, India", limit=5)
    assert results == [
        {
            "name": "Govindam Retreat",
            "rating": 4.4,
            "review_count": 9726,
            "price_level": "₹400–600",
            "address": "Gangori Bazaar, Jaipur, Rajasthan 302002, India",
            "description": "Traditional Rajasthani fare in plush, atmospheric interiors.",
            "types": ["Restaurant", "Breakfast restaurant"],
            "latitude": 26.9288767,
            "longitude": 75.8255344,
            "website": "https://govindamretreat.in",
        }
    ]


def test_search_restaurants_falls_back_to_type_when_no_subtypes(monkeypatch):
    monkeypatch.setattr(restaurants_api, "RAPIDAPI_KEY", "test-key")
    payload = {"data": [{"name": "Corner Cafe", "type": "Cafe"}]}
    monkeypatch.setattr(restaurants_api.requests, "get", lambda *a, **k: FakeResponse(200, payload))

    results = restaurants_api.search_restaurants("Jaipur, India")
    assert results[0]["types"] == ["Cafe"]


def test_search_restaurants_returns_empty_list_when_no_data(monkeypatch):
    monkeypatch.setattr(restaurants_api, "RAPIDAPI_KEY", "test-key")
    monkeypatch.setattr(restaurants_api.requests, "get", lambda *a, **k: FakeResponse(200, {"data": []}))
    assert restaurants_api.search_restaurants("Jaipur, India") == []


def test_get_raises_restaurants_api_error_on_http_error(monkeypatch):
    monkeypatch.setattr(restaurants_api, "RAPIDAPI_KEY", "test-key")
    monkeypatch.setattr(restaurants_api.requests, "get", lambda *a, **k: FakeResponse(500, {}, text="Server error"))
    with pytest.raises(restaurants_api.RestaurantsAPIError):
        restaurants_api.search_restaurants("Jaipur, India")
