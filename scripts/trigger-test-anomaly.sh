#!/bin/bash
# Quick script to inject a test anomaly into the database
# This bypasses the normal data pipeline to test anomaly detection

set -e

echo "🧪 Injecting test anomaly into database..."

docker compose -f docker/docker-compose.yml exec timescaledb psql -U gpu_monitor -d gpu_health << 'EOF'
-- Inject an extreme temperature spike (95°C - way above normal)
INSERT INTO gpu_metrics (
    time, gpu_uuid, hostname, gpu_temp, memory_temp, power_usage,
    throttle_reasons, sm_active, memory_utilization,
    fb_used_bytes, fb_free_bytes, fb_total_bytes,
    collection_latency_ms, validation_passed
) VALUES (
    NOW(),
    'GPU-abc123def456',
    'mock-gpu-node',
    95.0,  -- Extreme temperature!
    88.0,
    450,   -- High power
    256,   -- Thermal throttling
    100,
    85,
    68719476736,
    11811160064,
    80530636800,
    5,
    true
);

SELECT 'Anomaly injected! Temperature: 95°C (normal: ~73°C ± 6°C)';
SELECT 'Z-score: ' || ROUND(((95.0 - 72.8) / 5.8)::numeric, 2) || ' (threshold: 3.0)';
SELECT 'Next ML detector run will catch this if z-score > threshold';
EOF

echo ""
echo "✅ Test anomaly injected!"
echo ""
echo "Check anomalies in ~5 minutes (next detector cycle):"
echo "  docker compose -f docker/docker-compose.yml exec timescaledb psql -U gpu_monitor -d gpu_health -c 'SELECT * FROM anomalies ORDER BY time DESC LIMIT 5;'"
echo ""
echo "Or watch detector logs:"
echo "  docker compose -f docker/docker-compose.yml logs ml-detector -f"
