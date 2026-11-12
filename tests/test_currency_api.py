import requests

from services import currency_api


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_is_configured_is_always_true():
    assert currency_api.is_configured() is True


def test_get_rate_same_currency_returns_one_without_a_network_call(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("should not call the network for a same-currency pair")

    monkeypatch.setattr(currency_api.requests, "get", boom)
    currency_api._rate_cache.clear()
    result = currency_api.get_rate("USD", "usd")
    assert result == {"rate": 1.0, "date": None}


def test_get_rate_parses_real_response(monkeypatch):
    currency_api._rate_cache.clear()
    payload = {"amount": 1.0, "base": "USD", "date": "2026-11-12", "rates": {"INR": 93.69}}
    monkeypatch.setattr(currency_api.requests, "get", lambda *a, **k: FakeResponse(200, payload))
    result = currency_api.get_rate("USD", "INR")
    assert result == {"rate": 93.69, "date": "2026-11-12"}


def test_get_rate_caches_within_ttl(monkeypatch):
    currency_api._rate_cache.clear()
    calls = []

    def fake_get(*a, **k):
        calls.append(1)
        return FakeResponse(200, {"rates": {"INR": 93.69}, "date": "2026-11-12"})

    monkeypatch.setattr(currency_api.requests, "get", fake_get)
    currency_api.get_rate("USD", "INR")
    currency_api.get_rate("USD", "INR")
    assert len(calls) == 1  # second call served from cache


def test_get_rate_returns_none_on_http_error(monkeypatch):
    currency_api._rate_cache.clear()
    monkeypatch.setattr(currency_api.requests, "get", lambda *a, **k: FakeResponse(500, {}))
    assert currency_api.get_rate("USD", "ZZZ") is None


def test_get_rate_returns_none_on_network_error(monkeypatch):
    currency_api._rate_cache.clear()

    def boom(*a, **k):
        raise requests.RequestException("down")

    monkeypatch.setattr(currency_api.requests, "get", boom)
    assert currency_api.get_rate("USD", "INR") is None


def test_get_rate_returns_none_for_unknown_currency(monkeypatch):
    currency_api._rate_cache.clear()
    monkeypatch.setattr(currency_api.requests, "get", lambda *a, **k: FakeResponse(200, {"rates": {}}))
    assert currency_api.get_rate("USD", "ZZZ") is None


def test_convert_uses_real_rate(monkeypatch):
    currency_api._rate_cache.clear()
    monkeypatch.setattr(
        currency_api.requests, "get", lambda *a, **k: FakeResponse(200, {"rates": {"INR": 90.0}, "date": "2026-11-12"})
    )
    result = currency_api.convert(100, "USD", "INR")
    assert result == {
        "amount": 100, "from": "USD", "to": "INR", "rate": 90.0, "converted": 9000.0,
        "date": "2026-11-12", "source": "real",
    }


def test_convert_returns_none_when_rate_unavailable(monkeypatch):
    currency_api._rate_cache.clear()
    monkeypatch.setattr(currency_api.requests, "get", lambda *a, **k: FakeResponse(500, {}))
    assert currency_api.convert(100, "USD", "ZZZ") is None


def test_list_rates_parses_real_response(monkeypatch):
    payload = {"base": "USD", "date": "2026-11-12", "rates": {"INR": 93.69, "EUR": 0.92}}
    monkeypatch.setattr(currency_api.requests, "get", lambda *a, **k: FakeResponse(200, payload))
    result = currency_api.list_rates("usd")
    assert result == {"base": "USD", "date": "2026-11-12", "rates": {"INR": 93.69, "EUR": 0.92}, "source": "real"}


def test_list_rates_returns_none_on_error(monkeypatch):
    monkeypatch.setattr(currency_api.requests, "get", lambda *a, **k: FakeResponse(500, {}))
    assert currency_api.list_rates("USD") is None
