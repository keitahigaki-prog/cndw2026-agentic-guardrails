FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir opentelemetry-sdk==1.45.2 opentelemetry-exporter-otlp-proto-http==1.45.2
COPY agent.py mcp_tools.py collector.py otel_setup.py ./
