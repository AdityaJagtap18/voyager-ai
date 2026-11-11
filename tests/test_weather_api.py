import pytest

from services import weather_api


class FakeResponse:
    def __init__(self, status_code, payload, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or str(payload)

    def json(self):
        return self._payload


def test_is_configured_reflects_key_presence(monkeypatch):
    monkeypatch.setattr(weather_api, "OPENWEATHER_API_KEY", None)
    assert weather_api.is_configured() is False
    monkeypatch.setattr(weather_api, "OPENWEATHER_API_KEY", "key")
    assert weather_api.is_configured() is True


def test_geocode_requires_api_key(monkeypatch):
    monkeypatch.setattr(weather_api, "OPENWEATHER_API_KEY", None)
    with pytest.raises(weather_api.WeatherAPIError):
        weather_api.geocode("Goa")


def test_geocode_parses_first_result(monkeypatch):
    monkeypatch.setattr(weather_api, "OPENWEATHER_API_KEY", "test-key")
    payload = [{"lat": 15.4909, "lon": 73.8278, "name": "Goa", "country": "IN"}]
    monkeypatch.setattr(weather_api.requests, "get", lambda *a, **k: FakeResponse(200, payload))

    location = weather_api.geocode("Goa")
    assert location == {"lat": 15.4909, "lon": 73.8278, "name": "Goa", "country": "IN"}


def test_geocode_raises_when_no_results(monkeypatch):
    monkeypatch.setattr(weather_api, "OPENWEATHER_API_KEY", "test-key")
    monkeypatch.setattr(weather_api.requests, "get", lambda *a, **k: FakeResponse(200, []))
    with pytest.raises(weather_api.WeatherAPIError):
        weather_api.geocode("Nowhereistan")


def test_get_forecast_groups_by_date_and_picks_midday_description(monkeypatch):
    monkeypatch.setattr(weather_api, "OPENWEATHER_API_KEY", "test-key")

    def fake_get(url, params, **kwargs):
        if url == weather_api.GEOCODE_URL:
            return FakeResponse(200, [{"lat": 15.49, "lon": 73.82, "name": "Goa", "country": "IN"}])
        payload = {
            "list": [
                {"dt_txt": "2026-12-10 03:00:00", "main": {"temp": 24.0}, "weather": [{"description": "clear sky", "icon": "01n"}]},
                {"dt_txt": "2026-12-10 12:00:00", "main": {"temp": 30.5}, "weather": [{"description": "few clouds", "icon": "02d"}]},
                {"dt_txt": "2026-12-10 21:00:00", "main": {"temp": 26.0}, "weather": [{"description": "clear sky", "icon": "01n"}]},
                {"dt_txt": "2026-12-11 12:00:00", "main": {"temp": 29.0}, "weather": [{"description": "overcast clouds", "icon": "04d"}]},
            ]
        }
        return FakeResponse(200, payload)

    monkeypatch.setattr(weather_api.requests, "get", fake_get)

    forecast = weather_api.get_forecast("Goa")
    assert forecast["location"] == {"name": "Goa", "country": "IN"}
    assert forecast["days"] == [
        {"date": "2026-12-10", "temp_min": 24.0, "temp_max": 30.5, "description": "few clouds", "icon": "02d"},
        {"date": "2026-12-11", "temp_min": 29.0, "temp_max": 29.0, "description": "overcast clouds", "icon": "04d"},
    ]


def test_get_raises_weather_api_error_on_http_error(monkeypatch):
    monkeypatch.setattr(weather_api, "OPENWEATHER_API_KEY", "test-key")
    monkeypatch.setattr(weather_api.requests, "get", lambda *a, **k: FakeResponse(401, {}, text="Invalid API key"))
    with pytest.raises(weather_api.WeatherAPIError):
        weather_api.geocode("Goa")
