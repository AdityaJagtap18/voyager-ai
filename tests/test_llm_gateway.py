from config import Config
from llm_gateway import MODEL_REGISTRY, DEFAULT_MODEL, get_chat_model, is_configured, resolve_model


def test_resolve_model_prefers_explicit_known_id():
    assert resolve_model("gpt-4o") == "gpt-4o"


def test_resolve_model_falls_back_to_default_for_unknown_id(monkeypatch):
    monkeypatch.setattr(Config, "OPENAI_MODEL", "gpt-4o")
    assert resolve_model("not-a-real-model") == "gpt-4o"


def test_resolve_model_falls_back_to_configured_default_when_none_given(monkeypatch):
    monkeypatch.setattr(Config, "OPENAI_MODEL", "gpt-4o-mini")
    assert resolve_model(None) == "gpt-4o-mini"


def test_resolve_model_falls_back_to_hardcoded_default_if_configured_default_unknown(monkeypatch):
    monkeypatch.setattr(Config, "OPENAI_MODEL", "some-model-not-in-registry")
    assert resolve_model(None) == DEFAULT_MODEL


def test_is_configured_true_for_openai_model_with_key(monkeypatch):
    monkeypatch.setattr(Config, "OPENAI_API_KEY", "sk-test")
    assert is_configured("gpt-4o-mini") is True


def test_is_configured_false_for_openai_model_without_key(monkeypatch):
    monkeypatch.setattr(Config, "OPENAI_API_KEY", None)
    assert is_configured("gpt-4o-mini") is False


def test_is_configured_true_for_local_model_regardless_of_keys(monkeypatch):
    monkeypatch.setattr(Config, "OPENAI_API_KEY", None)
    assert is_configured("ollama/llama3") is True


def test_is_configured_false_for_unknown_model():
    assert is_configured("totally-made-up") is False


def test_model_registry_entries_have_required_fields():
    assert len(MODEL_REGISTRY) >= 4
    for model_id, info in MODEL_REGISTRY.items():
        assert info.id == model_id
        assert info.label
        assert info.provider
        assert info.context_window > 0


def test_get_chat_model_builds_a_langchain_compatible_model(monkeypatch):
    monkeypatch.setattr(Config, "OPENAI_API_KEY", "sk-test")
    model = get_chat_model("gpt-4o-mini", temperature=0.2)
    assert model.model == "gpt-4o-mini"
    assert model.temperature == 0.2


def test_get_chat_model_defaults_temperature_from_config(monkeypatch):
    monkeypatch.setattr(Config, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(Config, "OPENAI_TEMPERATURE", 0.9)
    model = get_chat_model("gpt-4o-mini")
    assert model.temperature == 0.9
