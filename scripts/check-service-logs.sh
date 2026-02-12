#!/bin/bash
# Check logs of all services for errors

cd "$(dirname "$0")/../docker"

echo "Checking service logs for errors..."
echo "===================================="
echo ""

SERVICES=(
    "mock-dcgm"
    "collector"
    "validator"
    "enricher"
    "timescale-sink"
    "health-scorer"
    "ml-detector"
    "alerting"
    "feature-engineering"
    "failure-predictor"
    "economic-engine"
    "api"
    "grafana"
    "mlflow"
)

for service in "${SERVICES[@]}"; do
    echo "--- $service ---"
    docker compose logs --tail=20 $service 2>/dev/null | grep -i "error\|exception\|failed\|traceback" | head -5 || echo "No errors found"
    echo ""
done

echo "===================================="
echo "Log check complete"
