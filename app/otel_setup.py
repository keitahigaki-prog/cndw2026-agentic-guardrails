"""OpenTelemetry の初期化（デモ用）。

■ このファイルの役割
  トレース（「1回のタスクで、何が、どの順に、どれだけ起きたか」の記録）を、
  OTLP/HTTP で、バックエンド（このデモでは Jaeger）へ送る設定をする。
  agent.py（エージェント）と mcp_tools.py（ツールサーバー）が、それぞれ呼ぶ。

■ OTEL_EXPORTER_OTLP_ENDPOINT が未設定なら、何もしない
  opentelemetry-api は、SDK を設定しないと「何もしない」実装（no-op）で動く。
  そのため、計装のコードを入れたままでも、バックエンドがなければ、従来どおり動く。

■ スパンを、1つ終わるたびに、すぐ送る（SimpleSpanProcessor）
  本番では、まとめて送る BatchSpanProcessor が普通。ただし、このデモでは Falco Talon が
  Pod を途中で終了させる。まとめ送りだと、止められた時点で、未送信のスパンが消える。
  すぐ送れば、止められるまでに終わったスパンは、Jaeger に残る（原因の調査に使える）。

■ 送信のタイムアウトは2秒
  デモ2では、NetworkPolicy が外向きを絞る。送れないときに、エージェントが長く待たされないため。

■ リソース属性（k8s.pod.name など）
  Pod のマニフェストが OTEL_RESOURCE_ATTRIBUTES で渡す。Resource.create が、自動で読む。
  Falco のアラートにも k8s.pod.name があるので、これが「検知とトレースをつなぐキー」になる。
"""
import os
from opentelemetry import trace


def enabled():
    return bool(os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"))


def init(service_name):
    if enabled():
        # SDK とエクスポータは、有効なときだけ import する（無効なら、import も不要）
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        # service.name は、Jaeger の画面で、サービスの名前（coding-agent / mcp-tools）として出る
        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(timeout=2)))
        trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)
