"""
Tests for app/observability (Phase 12): span creation, parent-child
relationships, redaction, exporter-failure isolation, and disabled-mode
behavior. These exercise the SDK directly (not through FastAPI) so they
don't depend on whether OTEL_ENABLED is set in this process's .env - each
test builds its own isolated TracerProvider.
"""
import pytest
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

import app.observability as obs_module
from app.observability import record_llm_usage, traced_span
from app.observability.redaction import redact_attributes


@pytest.fixture
def otel_provider(monkeypatch):
    """Builds an isolated TracerProvider + in-memory exporter and points
    app.observability.get_tracer() at it for the duration of one test. The
    OTel API deliberately refuses to let a process call
    trace.set_tracer_provider() more than once ("Overriding of current
    TracerProvider is not allowed") - exactly the kind of global mutable
    state that makes swapping the *global* provider across tests unsafe, so
    this monkeypatches the one function Voyager's own code calls to get a
    tracer instead, which is the supported way to isolate tests per the
    SDK's own design."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": "test"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")

    monkeypatch.setattr(obs_module, "get_tracer", lambda name="voyager": tracer)
    yield exporter


def test_traced_span_records_attributes_and_ok_status(otel_provider):
    with traced_span("voyager.trip.generate", **{"voyager.trip_id": "abc123", "llm.model": "gpt-4o-mini"}):
        pass

    spans = otel_provider.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "voyager.trip.generate"
    assert spans[0].attributes["voyager.trip_id"] == "abc123"
    assert spans[0].status.status_code == trace.StatusCode.OK


def test_traced_span_records_exception_and_reraises(otel_provider):
    with pytest.raises(ValueError):
        with traced_span("agent.research"):
            raise ValueError("provider outage")

    spans = otel_provider.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].status.status_code == trace.StatusCode.ERROR
    assert any(e.name == "exception" for e in spans[0].events)


def test_nested_spans_have_correct_parent_child_relationship(otel_provider):
    with traced_span("voyager.trip.generate") as parent:
        with traced_span("agent.research") as child:
            pass

    spans = otel_provider.get_finished_spans()
    # Exporter sees child first (it finishes first), then parent.
    child_span = next(s for s in spans if s.name == "agent.research")
    parent_span = next(s for s in spans if s.name == "voyager.trip.generate")
    assert child_span.parent.span_id == parent_span.context.span_id
    assert child_span.context.trace_id == parent_span.context.trace_id
    assert parent is not None and child is not None


def test_context_propagates_across_plain_function_calls(otel_provider):
    """Context propagation (Part 3.3) through ordinary synchronous Python
    calls - no threads/async involved - which is how workflow.py's node
    functions and crewai_adapter.py's tool closures actually run."""
    def inner():
        with traced_span("agent.flights"):
            pass

    with traced_span("voyager.trip.generate"):
        inner()

    spans = otel_provider.get_finished_spans()
    child = next(s for s in spans if s.name == "agent.flights")
    parent = next(s for s in spans if s.name == "voyager.trip.generate")
    assert child.parent.span_id == parent.context.span_id


def test_record_llm_usage_never_writes_zero_for_missing_data(otel_provider):
    with traced_span("llm.request") as span:
        record_llm_usage(span, model="gpt-4o-mini", provider="openai", input_tokens=None, output_tokens=None)

    attrs = otel_provider.get_finished_spans()[0].attributes
    assert attrs["llm.model"] == "gpt-4o-mini"
    assert "llm.usage.input_tokens" not in attrs
    assert "llm.usage.total_tokens" not in attrs


def test_record_llm_usage_writes_real_counts_when_present(otel_provider):
    with traced_span("llm.request") as span:
        record_llm_usage(span, model="gpt-4o-mini", provider="openai", input_tokens=120, output_tokens=45)

    attrs = otel_provider.get_finished_spans()[0].attributes
    assert attrs["llm.usage.input_tokens"] == 120
    assert attrs["llm.usage.output_tokens"] == 45
    assert attrs["llm.usage.total_tokens"] == 165


def test_traced_span_is_harmless_noop_when_tracing_disabled():
    """No fixture here - this runs against whatever global tracer provider
    is already installed (the no-op default, since nothing in the test
    process calls configure_observability() with OTEL_ENABLED=true unless
    another test's fixture is active). Must not raise."""
    with traced_span("voyager.trip.generate", **{"voyager.trip_id": "x"}):
        pass


# --- Redaction (Part 10) -----------------------------------------------------


def test_redact_attributes_blanks_credential_shaped_keys():
    out = redact_attributes({"api_key": "sk-abc123", "Authorization": "Bearer xyz", "ok_field": "fine"})
    assert out["api_key"] == "[REDACTED]"
    assert out["Authorization"] == "[REDACTED]"
    assert out["ok_field"] == "fine"


def test_redact_attributes_scrubs_credential_shaped_values_in_otherwise_safe_fields():
    out = redact_attributes({"log_line": "called with key sk-abcdefghijklmnop ok"})
    assert "sk-abcdefghijklmnop" not in out["log_line"]
    assert "[REDACTED]" in out["log_line"]


def test_redact_attributes_does_not_mutate_input():
    original = {"api_key": "secret"}
    redact_attributes(original)
    assert original["api_key"] == "secret"


def test_redact_attributes_keeps_token_usage_counts():
    """Regression: a plain substring match for "token" also matched inside
    "tokens" (plural, a count) - wiping out llm.usage.*_tokens as if they
    were credentials. These must survive redaction untouched."""
    out = redact_attributes(
        {"llm.usage.input_tokens": 120, "llm.usage.output_tokens": 45, "llm.usage.total_tokens": 165}
    )
    assert out["llm.usage.input_tokens"] == 120
    assert out["llm.usage.output_tokens"] == 45
    assert out["llm.usage.total_tokens"] == 165


def test_redact_attributes_still_redacts_singular_token_keys():
    out = redact_attributes({"access_token": "abc123", "api_token": "xyz789"})
    assert out["access_token"] == "[REDACTED]"
    assert out["api_token"] == "[REDACTED]"


# --- Exporter failure isolation (Part 12) -----------------------------------


def test_db_span_exporter_failure_does_not_raise(monkeypatch):
    """export() must return FAILURE, never raise, when persistence breaks -
    this is what keeps a DB hiccup from becoming a BatchSpanProcessor
    background-thread crash, let alone a request-path failure."""
    from app.observability import DBSpanExporter
    from opentelemetry.sdk.trace.export import SpanExportResult

    def boom(self, spans):
        raise RuntimeError("db is down")

    monkeypatch.setattr(DBSpanExporter, "_write", boom)
    exporter = DBSpanExporter()
    result = exporter.export([])
    assert result == SpanExportResult.FAILURE


def test_configure_observability_noop_when_otel_disabled(monkeypatch):
    from app import observability as obs_module
    from app.config import Config

    monkeypatch.setattr(Config, "OTEL_ENABLED", False)
    monkeypatch.setattr(obs_module, "_configured", False)
    obs_module.configure_observability()
    assert obs_module._configured is False
