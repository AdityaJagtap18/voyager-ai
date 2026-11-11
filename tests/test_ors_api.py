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


def test_search_places_requires_api_key(monkeypatch):
    monkeypatch.setattr(ors_api, "ORS_API_KEY", None)
    with pytest.raises(ors_api.ORSError):
        ors_api.search_places("Mumbai")


def test_search_places_parses_label_and_coordinates(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "features": [
                    {
                        "geometry": {"coordinates": [72.8777, 19.0760]},
                        "properties": {"label": "Mumbai, Maharashtra, India"},
                    }
                ]
            }

    monkeypatch.setattr(ors_api, "ORS_API_KEY", "test-key")
    monkeypatch.setattr(ors_api.requests, "get", lambda *a, **k: FakeResponse())

    results = ors_api.search_places("Mumbai")
    assert results == [{"label": "Mumbai, Maharashtra, India", "lat": 19.0760, "lng": 72.8777}]


def test_search_places_raises_on_error_status(monkeypatch):
    class FakeResponse:
        status_code = 500

        def json(self):
            return {}

        text = "server error"

    monkeypatch.setattr(ors_api, "ORS_API_KEY", "test-key")
    monkeypatch.setattr(ors_api.requests, "get", lambda *a, **k: FakeResponse())

    with pytest.raises(ors_api.ORSError):
        ors_api.search_places("Nowhere")


def test_get_route_requires_api_key(monkeypatch):
    monkeypatch.setattr(ors_api, "ORS_API_KEY", None)
    with pytest.raises(ors_api.ORSError):
        ors_api.get_route((0, 0), (1, 1))


def test_decode_polyline_matches_known_vector():
    # Standard Google polyline algorithm test vector (precision 5):
    # https://developers.google.com/maps/documentation/utilities/polylinealgorithm
    coords = ors_api._decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@")
    assert coords == [(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]


def test_get_route_parses_real_api_shape(monkeypatch):
    # The real ORS directions endpoint (POST /v2/directions/{profile}) returns
    # {"routes": [...]} with an encoded polyline geometry, not GeoJSON
    # "features" — confirmed live against the real API. The old code assumed
    # the GeoJSON shape and silently raised ORSError on every real call.
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "routes": [
                    {
                        "summary": {"distance": 594000.0, "duration": 36000.0},
                        "geometry": "_p~iF~ps|U_ulLnnqC_mqNvxq`@",
                    }
                ]
            }

    monkeypatch.setattr(ors_api, "ORS_API_KEY", "test-key")
    monkeypatch.setattr(ors_api.requests, "post", lambda *a, **k: FakeResponse())

    route = ors_api.get_route((19.0760, 72.8777), (15.4909, 73.8278))
    assert route == {
        "distance_km": 594.0,
        "duration_h": 10.0,
        "geometry": [[38.5, -120.2], [40.7, -120.95], [43.252, -126.453]],
    }


def test_get_route_raises_on_missing_routes_key(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"features": []}  # the old, wrong shape — must not be accepted silently

    monkeypatch.setattr(ors_api, "ORS_API_KEY", "test-key")
    monkeypatch.setattr(ors_api.requests, "post", lambda *a, **k: FakeResponse())

    with pytest.raises(ors_api.ORSError):
        ors_api.get_route((0, 0), (1, 1))


def test_route_distance_duration_parses_real_api_shape(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"routes": [{"summary": {"distance": 594000.0, "duration": 36000.0}, "geometry": "..."}]}

    monkeypatch.setattr(ors_api, "ORS_API_KEY", "test-key")
    monkeypatch.setattr(ors_api.requests, "post", lambda *a, **k: FakeResponse())

    km, hours = ors_api.route_distance_duration((19.0760, 72.8777), (15.4909, 73.8278))
    assert (km, hours) == (594.0, 10.0)


def test_get_route_raises_on_error_status(monkeypatch):
    class FakeResponse:
        status_code = 400

        def json(self):
            return {"error": {"message": "no route found"}}

        text = "no route found"

    monkeypatch.setattr(ors_api, "ORS_API_KEY", "test-key")
    monkeypatch.setattr(ors_api.requests, "post", lambda *a, **k: FakeResponse())

    with pytest.raises(ors_api.ORSError):
        ors_api.get_route((0, 0), (1, 1))
