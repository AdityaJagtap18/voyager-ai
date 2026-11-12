from services import geocoding
from services.ors_api import ORSError


def test_geocode_attractions_adds_coordinates(monkeypatch):
    calls = []

    def fake_geocode(text, limit=1):
        calls.append(text)
        if text == "Jaipur, India":
            return [(26.9, 75.8)]
        return [(26.92, 75.82)]

    monkeypatch.setattr(geocoding, "geocode", fake_geocode)

    attractions = [{"name": "Hawa Mahal"}]
    result = geocoding.geocode_attractions(attractions, "Jaipur, India")

    assert result[0]["coordinates"] == {"lat": 26.92, "lng": 75.82}


def test_geocode_attractions_skips_already_geocoded(monkeypatch):
    geocode_calls = []
    monkeypatch.setattr(
        geocoding, "geocode", lambda text, limit=1: geocode_calls.append(text) or [(1.0, 2.0)]
    )

    attractions = [{"name": "Already done", "coordinates": {"lat": 9.0, "lng": 9.0}}]
    result = geocoding.geocode_attractions(attractions, "Jaipur, India")

    assert result[0]["coordinates"] == {"lat": 9.0, "lng": 9.0}
    assert geocode_calls == []


def test_geocode_attractions_removes_implausibly_far_match(monkeypatch):
    def fake_geocode(text, limit=1):
        if text == "Jaipur, India":
            return [(26.9, 75.8)]
        return [(9.97, 76.28)]  # ~2300km away, a different-city false match

    monkeypatch.setattr(geocoding, "geocode", fake_geocode)

    attractions = [{"name": "Hotel Pearl Palace"}]
    result = geocoding.geocode_attractions(attractions, "Jaipur, India")

    assert result[0]["coordinates"] is None
    assert result[0]["geocoding_error"] is True


def test_geocode_attractions_sets_none_on_no_match(monkeypatch):
    monkeypatch.setattr(geocoding, "geocode", lambda text, limit=1: [])

    attractions = [{"name": "Nowhere"}]
    result = geocoding.geocode_attractions(attractions, "Jaipur, India")

    assert result[0]["coordinates"] is None


def test_geocode_attractions_sets_none_on_provider_error(monkeypatch):
    def fake_geocode(text, limit=1):
        raise ORSError("provider down")

    monkeypatch.setattr(geocoding, "geocode", fake_geocode)

    attractions = [{"name": "Hawa Mahal"}]
    result = geocoding.geocode_attractions(attractions, "Jaipur, India")

    assert result[0]["coordinates"] is None


def test_geocode_attractions_skips_validation_when_center_unresolvable(monkeypatch):
    def fake_geocode(text, limit=1):
        if text == "Jaipur, India":
            return []
        return [(26.92, 75.82)]

    monkeypatch.setattr(geocoding, "geocode", fake_geocode)

    attractions = [{"name": "Hawa Mahal"}]
    result = geocoding.geocode_attractions(attractions, "Jaipur, India")

    # Validation skipped (no center to compare against), but the geocode itself still stands.
    assert result[0]["coordinates"] == {"lat": 26.92, "lng": 75.82}


def test_haversine_distance_known_values():
    # Roughly the straight-line distance between Jaipur and Kochi.
    distance = geocoding.haversine_distance((26.9, 75.8), (9.97, 76.28))
    assert 1800 < distance < 2400
