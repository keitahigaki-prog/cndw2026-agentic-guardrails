"""OpenTelemetry の初期化（デモ用）。
OTEL_EXPORTER_OTLP_ENDPOINT が未設定なら、何もしない（計装なしの従来どおりに動く）。
スパンは、1つ終わるたびに、すぐ送る（SimpleSpanProcessor）。Talon に Pod を止められても、
それまでに終わったスパンは、バックエンドに残るようにするため。"""
import os
from opentelemetry import trace


def enabled():
    return bool(os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"))


def init(service_name):
    if enabled():
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        # OTEL_RESOURCE_ATTRIBUTES（k8s.pod.name など）も、Resource.create が読む
        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        # 送れないときに、デモを止めないよう、タイムアウトは短く（2秒）
        provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(timeout=2)))
        trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)
