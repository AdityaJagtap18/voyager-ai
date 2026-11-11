from config import Config


def test_validate_raises_without_api_key(monkeypatch):
    monkeypatch.setattr(Config, "OPENAI_API_KEY", None)
    try:
        Config.validate()
    except ValueError as exc:
        assert "OPENAI_API_KEY" in str(exc)
    else:
        assert False, "expected ValueError when OPENAI_API_KEY is missing"


def test_validate_passes_with_api_key(monkeypatch):
    monkeypatch.setattr(Config, "OPENAI_API_KEY", "sk-test-key")
    assert Config.validate() is True


def test_defaults():
    assert Config.APP_NAME == "Voyager"
    assert Config.OPENAI_MODEL
    assert isinstance(Config.OPENAI_TEMPERATURE, float)
