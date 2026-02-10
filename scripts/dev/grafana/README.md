# Grafana LGTM Stack for Local Development

Single-container observability stack with **Loki** (logs), **Grafana** (visualization), **Tempo** (traces), and **Mimir** (metrics).

## Quick Start

```bash
# Start the stack
./scripts/dev/start-grafana.sh

# Or manually with docker-compose
cd scripts/dev/grafana && docker-compose up -d
```

## Access

- **Grafana UI**: http://localhost:3000
  - No login required (anonymous admin enabled for dev)
  - Username/Password (if needed): `admin` / `admin`

## Configure Hindsight API

Set these environment variables in your `.env`:

```bash
# Enable tracing
HINDSIGHT_API_OTEL_TRACES_ENABLED=true

# Grafana Tempo OTLP endpoint (HTTP)
HINDSIGHT_API_OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318

# Optional: Custom service name
HINDSIGHT_API_OTEL_SERVICE_NAME=hindsight-api

# Optional: Deployment environment
HINDSIGHT_API_OTEL_DEPLOYMENT_ENVIRONMENT=development
```

## View Traces

1. Open Grafana: http://localhost:3000
2. Go to **Explore** (compass icon in sidebar)
3. Select **Tempo** as the data source
4. Run a Hindsight operation (retain, recall, reflect)
5. Click "Search" to see recent traces
6. Click on a trace to see the full span hierarchy

## Features

- **Traces**: Full OpenTelemetry trace support with GenAI semantic conventions
- **Metrics**: Prometheus-compatible metrics (future)
- **Logs**: Loki log aggregation (future)
- **Single Container**: Everything in one Docker image (~200MB)

## Ports

| Port | Service |
|------|---------|
| 3000 | Grafana UI |
| 4317 | OTLP gRPC endpoint |
| 4318 | OTLP HTTP endpoint |

## Stop

```bash
cd scripts/dev/grafana && docker-compose down
```

## Learn More

- [Grafana docker-otel-lgtm](https://github.com/grafana/docker-otel-lgtm)
- [Grafana Tempo Documentation](https://grafana.com/docs/tempo/latest/)
- [OpenTelemetry with Grafana](https://grafana.com/docs/opentelemetry/)
