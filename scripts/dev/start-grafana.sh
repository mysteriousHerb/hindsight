#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GRAFANA_DIR="$SCRIPT_DIR/grafana"

cd "$GRAFANA_DIR"

echo "🚀 Starting Grafana LGTM Stack (Loki, Grafana, Tempo, Mimir)..."
echo ""
echo "This provides:"
echo "  • OpenTelemetry tracing (Tempo)"
echo "  • Metrics (Mimir)"
echo "  • Logs (Loki)"
echo "  • Visualization (Grafana)"
echo ""

docker-compose up -d

echo ""
echo "✅ Grafana LGTM Stack started!"
echo ""
echo "Access Grafana UI: http://localhost:3000"
echo "  (no login required for dev - anonymous admin enabled)"
echo ""
echo "OTLP Endpoints:"
echo "  • HTTP: http://localhost:4318"
echo "  • gRPC: http://localhost:4317"
echo ""
echo "Configure Hindsight API with:"
echo "  export HINDSIGHT_API_OTEL_TRACES_ENABLED=true"
echo "  export HINDSIGHT_API_OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318"
echo ""
echo "View traces:"
echo "  1. Open http://localhost:3000"
echo "  2. Click 'Explore' (compass icon)"
echo "  3. Select 'Tempo' as data source"
echo "  4. Click 'Search' to see traces"
echo ""
echo "Stop with: cd $GRAFANA_DIR && docker-compose down"
