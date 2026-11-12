"""
Observability (Phase 12): OpenTelemetry as the common instrumentation layer,
with LangSmith (via LangChain's own env-var-driven tracing) and Arize Phoenix
(via a second OTLP exporter on the same provider) as optional backends on
top of it.

Everything here is additive and fails open:
  - If OTEL_ENABLED is false (the default), configure() does nothing and
    every tracer this module hands out is the OpenTelemetry API's built-in
    no-op implementation (that's the API's own default when no SDK
    TracerProvider has been registered - not something this module has to
    special-case).
  - If an exporter (OTLP collector, Phoenix) is unreachable, span export
    failures are caught inside BatchSpanProcessor's own background thread
    and logged - they never propagate to the request that created the span,
    and they never raise out of configure() itself.
  - LangSmith tracing is entirely LangChain's own mechanism, switched on by
    the LANGSMITH_TRACING/LANGSMITH_API_KEY/LANGSMITH_PROJECT env vars that
    app/config.py's load_dotenv() already puts into os.environ - no explicit
    wiring is needed for LangChain-based LLM calls (every agent's
    ChatLiteLLM instance), and if LangSmith's API is unreachable, LangChain's
    own background tracer swallows the error rather than failing the run.

See docs/VOYAGER_TECH_STACK.md Part 10/15 for what this replaces (nothing
real existed before this phase) and docs/VOYAGER_IMPLEMENTATION_AUDIT.md for
the phase-by-phase build log.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.sdk.trace.sampling import ALWAYS_OFF, ALWAYS_ON, TraceIdRatioBased
from opentelemetry.trace import Status, StatusCode

from app.config import Config
from app.observability.redaction import redact_attributes
from utils.logger import logger

_configured = False


def _build_sampler():
    name = (Config.OTEL_TRACES_SAMPLER or "always_on").lower()
    if name == "always_off":
        return ALWAYS_OFF
    if name == "traceidratio":
        return TraceIdRatioBased(Config.OTEL_TRACES_SAMPLER_ARG)
    return ALWAYS_ON


class DBSpanExporter(SpanExporter):
    """Writes finished spans into the `spans` table (app/models_db.py's
    Span) so Voyager's own Observability UI has a real trace store to read,
    independent of whether any external backend is also configured. Runs
    inside BatchSpanProcessor's background export thread - never raises, so
    a DB hiccup here can't affect the request that created the span."""

    def export(self, spans) -> SpanExportResult:
        try:
            self._write(spans)
            return SpanExportResult.SUCCESS
        except Exception as exc:  # noqa: BLE001 - exporters must never raise
            logger.warning(f"Observability: failed to persist {len(spans)} span(s) to DB: {exc}")
            return SpanExportResult.FAILURE

    def _write(self, spans) -> None:
        from app.db import SessionLocal
        from app.models_db import Span as SpanModel

        db = SessionLocal()
        try:
            trace_ids = set()
            for span in spans:
                row = _to_span_row(span, SpanModel)
                db.add(row)
                trace_ids.add(row.trace_id)
            db.flush()

            # Only the root "voyager.trip.generate" span carries
            # voyager.trip_id (it's the one place api.py's create_trip
            # actually knows it) - backfill it onto every other span in the
            # same trace so the trace explorer can filter "spans for trip X"
            # without depending on export batch order (a trace's spans can
            # legitimately arrive across more than one BatchSpanProcessor
            # flush).
            for trace_id in trace_ids:
                known = (
                    db.query(SpanModel.trip_id)
                    .filter(SpanModel.trace_id == trace_id, SpanModel.trip_id.isnot(None))
                    .first()
                )
                if known and known[0]:
                    db.query(SpanModel).filter(
                        SpanModel.trace_id == trace_id, SpanModel.trip_id.is_(None)
                    ).update({"trip_id": known[0]}, synchronize_session=False)
            db.commit()
        finally:
            db.close()

    def shutdown(self) -> None:
        pass


def _to_span_row(span: ReadableSpan, SpanModel):
    ctx = span.get_span_context()
    parent = span.parent
    status = span.status
    status_label = "unset"
    if status.status_code == StatusCode.OK:
        status_label = "ok"
    elif status.status_code == StatusCode.ERROR:
        status_label = "error"

    attributes = redact_attributes(dict(span.attributes or {}))
    start = datetime.fromtimestamp((span.start_time or 0) / 1e9, tz=timezone.utc)
    end = datetime.fromtimestamp((span.end_time or span.start_time or 0) / 1e9, tz=timezone.utc)

    return SpanModel(
        trace_id=format(ctx.trace_id, "032x"),
        span_id=format(ctx.span_id, "016x"),
        parent_span_id=format(parent.span_id, "016x") if parent is not None else None,
        name=span.name,
        trip_id=attributes.get("voyager.trip_id"),
        start_time=start,
        end_time=end,
        duration_ms=round(((span.end_time or 0) - (span.start_time or 0)) / 1e6, 2),
        status=status_label,
        status_message=status.description,
        attributes=attributes,
        resource=dict(span.resource.attributes) if span.resource else {},
        events=[
            {"name": e.name, "timestamp": e.timestamp, "attributes": redact_attributes(dict(e.attributes or {}))}
            for e in (span.events or [])
        ],
    )


def configure_observability(app=None, engine=None) -> None:
    """Call once at startup (app/api.py's module scope). No-op unless
    OTEL_ENABLED=true. Idempotent - safe to call more than once (tests do)."""
    global _configured
    if not Config.OTEL_ENABLED:
        logger.info("Observability: OTEL_ENABLED is false, tracing disabled (no-op tracer)")
        return
    if _configured:
        return

    resource = Resource.create(
        {
            "service.name": Config.OTEL_SERVICE_NAME,
            "deployment.environment": Config.OTEL_ENVIRONMENT,
        }
    )
    provider = TracerProvider(resource=resource, sampler=_build_sampler())

    provider.add_span_processor(BatchSpanProcessor(DBSpanExporter()))

    if Config.OTEL_EXPORTER_OTLP_ENDPOINT:
        provider.add_span_processor(BatchSpanProcessor(_otlp_exporter(Config.OTEL_EXPORTER_OTLP_ENDPOINT)))

    if Config.PHOENIX_ENABLED:
        # Phoenix speaks plain OTLP/HTTP - a second exporter on the same
        # provider, not a competing TracerProvider (phoenix.otel.register()
        # would create its own; using it here would mean every span is
        # evaluated against which provider is "current," which is exactly
        # the duplicate-instrumentation rule 9 for this phase).
        endpoint = Config.PHOENIX_COLLECTOR_ENDPOINT.rstrip("/") + "/v1/traces"
        headers = {"Authorization": f"Bearer {Config.PHOENIX_API_KEY}"} if Config.PHOENIX_API_KEY else None
        provider.add_span_processor(
            BatchSpanProcessor(_otlp_exporter(endpoint, protocol="http/protobuf", headers=headers))
        )

    trace.set_tracer_provider(provider)
    _configured = True

    if app is not None:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(app)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Observability: FastAPI instrumentation failed: {exc}")

    if engine is not None:
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

            SQLAlchemyInstrumentor().instrument(engine=engine)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Observability: SQLAlchemy instrumentation failed: {exc}")

    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor

        RequestsInstrumentor().instrument()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Observability: requests instrumentation failed: {exc}")

    logger.info(
        f"Observability: tracing enabled (service={Config.OTEL_SERVICE_NAME}, "
        f"otlp={'yes' if Config.OTEL_EXPORTER_OTLP_ENDPOINT else 'no'}, phoenix={Config.PHOENIX_ENABLED})"
    )


def _otlp_exporter(endpoint: str, protocol: Optional[str] = None, headers: Optional[dict] = None):
    proto = (protocol or Config.OTEL_EXPORTER_OTLP_PROTOCOL or "http/protobuf").lower()
    if proto == "grpc":
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as GrpcExporter

        return GrpcExporter(endpoint=endpoint, headers=headers)
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HttpExporter

    return HttpExporter(endpoint=endpoint, headers=headers)


def get_tracer(name: str = "voyager"):
    return trace.get_tracer(name)


@contextmanager
def traced_span(name: str, **attributes) -> Iterator[Optional[trace.Span]]:
    """Context manager for a custom span with Voyager-specific attributes.
    Records exceptions and re-raises them unchanged - this never swallows a
    real application error, it only annotates the span before it propagates.
    A no-op tracer (OTel disabled) makes this a harmless pass-through."""
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key, value)
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


def record_llm_usage(span: Optional[trace.Span], *, model: Optional[str], provider: Optional[str],
                      input_tokens: Optional[int], output_tokens: Optional[int]) -> None:
    """Sets token-usage attributes on a span, distinguishing "the provider
    didn't report usage" (attributes simply absent) from "usage was zero" -
    never writes a 0 that wasn't actually reported, per the strict rule
    against displaying missing data as zero."""
    if span is None:
        return
    if model:
        span.set_attribute("llm.model", model)
    if provider:
        span.set_attribute("llm.provider", provider)
    if input_tokens is not None:
        span.set_attribute("llm.usage.input_tokens", input_tokens)
    if output_tokens is not None:
        span.set_attribute("llm.usage.output_tokens", output_tokens)
    if input_tokens is not None and output_tokens is not None:
        span.set_attribute("llm.usage.total_tokens", input_tokens + output_tokens)
