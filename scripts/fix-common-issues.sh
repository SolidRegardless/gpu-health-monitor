#!/bin/bash
# GPU Health Monitor - Common Issue Fixes

set -e

cd "$(dirname "$0")/../docker"

echo "GPU Health Monitor - Issue Fixer"
echo "================================="
echo ""

# Issue 1: Remove docker-compose version warning
echo "1. Removing docker-compose version attribute..."
sed -i '/^version:/d' docker-compose.yml
echo "✓ Removed version attribute"
echo ""

# Issue 2: Ensure all schema files are applied
echo "2. Applying database schemas..."
for schema in ../schema/*.sql; do
    echo "  - Applying $(basename $schema)..."
    docker compose exec -T timescaledb psql -U gpu_monitor -d gpu_health < "$schema" 2>&1 | grep -E "(CREATE|SELECT|GRANT|INSERT|ERROR)" | head -5
done
echo "✓ All schemas applied"
echo ""

# Issue 3: Restart services with issues
echo "3. Checking for crashed services..."
CRASHED=$(docker compose ps --filter "status=exited" --format "{{.Name}}")
if [ -n "$CRASHED" ]; then
    echo "Found crashed services:"
    echo "$CRASHED"
    echo "Restarting..."
    docker compose up -d
else
    echo "✓ No crashed services"
fi
echo ""

# Issue 4: Clear old Kafka data if needed
echo "4. Kafka health check..."
KAFKA_HEALTH=$(docker compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092 2>&1 | grep -c "ApiVersion" || echo "0")
if [ "$KAFKA_HEALTH" -gt 0 ]; then
    echo "✓ Kafka healthy"
else
    echo "⚠ Kafka may have issues, consider: docker compose restart kafka"
fi
echo ""

# Issue 5: Check TimescaleDB extensions
echo "5. Checking TimescaleDB extensions..."
docker compose exec -T timescaledb psql -U gpu_monitor -d gpu_health -c "SELECT extname, extversion FROM pg_extension WHERE extname IN ('timescaledb', 'pg_stat_statements');" 2>&1 | grep -E "timescaledb|pg_stat"
echo "✓ Extensions checked"
echo ""

echo "================================="
echo "Fix script complete!"
echo "Run ./system-health-check.sh to verify"
echo ""
