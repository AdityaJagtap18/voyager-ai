import pytest

from services import ors_api


def test_route_distance_duration_requires_api_key(monkeypatch):
    monkeypatch.setattr(ors_api, "ORS_API_KEY", None)
    with pytest.raises(ors_api.ORSError):
        ors_api.route_distance_duration((0, 0), (1, 1))


def test_matrix_distances_requires_api_key(monkeypatch):
    monkeypatch.setattr(ors_api, "ORS_API_KEY", None)
    with pytest.raises(ors_api.ORSError):
        ors_api.matrix_distances((0, 0), [(1, 1)])


def test_geocode_parses_features(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "features": [
                    {"geometry": {"coordinates": [72.8777, 19.0760]}},  # ORS: [lng, lat]
                ]
            }

    monkeypatch.setattr(ors_api, "ORS_API_KEY", "test-key")
    monkeypatch.setattr(ors_api.requests, "get", lambda *a, **k: FakeResponse())

    coords = ors_api.geocode("Mumbai, India")
    assert coords == [(19.0760, 72.8777)]


def test_geocode_raises_on_error_status(monkeypatch):
    class FakeResponse:
        status_code = 400

        def json(self):
            return {"error": {"message": "bad request"}}

        text = "bad request"

    monkeypatch.setattr(ors_api, "ORS_API_KEY", "test-key")
    monkeypatch.setattr(ors_api.requests, "get", lambda *a, **k: FakeResponse())

    with pytest.raises(ors_api.ORSError):
        ors_api.geocode("Nowhere")


def test_matrix_distances_maps_results(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "distances": [[5000.0, None]],
                "durations": [[600.0, None]],
            }

    monkeypatch.setattr(ors_api, "ORS_API_KEY", "test-key")
    monkeypatch.setattr(ors_api.requests, "post", lambda *a, **k: FakeResponse())

    results = ors_api.matrix_distances((0, 0), [(1, 1), (2, 2)])
    assert results[0] == {"distance_km": 5.0, "duration_h": 0.17, "status": "OK", "error": None}
    assert results[1]["status"] == "ERR"
