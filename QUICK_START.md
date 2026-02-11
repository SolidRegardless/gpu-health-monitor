# GPU Health Monitor - Quick Start Guide

## Complete System Deployment

This guide will get the entire GPU Health Monitor system running locally with all components.

## Prerequisites

- Docker and Docker Compose installed
- 8GB+ RAM available
- Ports available: 2181, 9092, 9093, 5432, 3000, 8000, 9400

## Step-by-Step Deployment

### 1. Start Core Infrastructure

```bash
cd /home/hart/.openclaw/workspace/gpu-health-monitor/docker

# Start Zookeeper, Kafka, and TimescaleDB
docker-compose up -d zookeeper kafka timescaledb

# Wait for services to initialize (~30 seconds)
sleep 30

# Verify services are healthy
docker-compose ps
```

All three services should show "Up" status.

### 2. Start Data Collection

```bash
# Start mock DCGM and collector
docker-compose up -d mock-dcgm collector

# Wait 10 seconds for startup
sleep 10

# Verify mock DCGM is serving metrics
curl http://localhost:9400/metrics | head -20
```

You should see Prometheus-format metrics for a simulated A100 GPU.

### 3. Start Stream Processors

```bash
# Start validator and enricher
docker-compose up -d validator enricher

# Wait 10 seconds
sleep 10

# Start TimescaleDB sink
docker-compose up -d timescale-sink

# View logs to verify data flow
docker-compose logs -f --tail=20 validator
# Press Ctrl+C after seeing "Processed X events" messages
```

### 4. Start Analytics & API

```bash
# Start health scorer and API
docker-compose up -d health-scorer api

# Wait 10 seconds
sleep 10

# Verify API is running
curl http://localhost:8000/health
```

Expected response: `{"status":"healthy","database":"connected"}`

### 5. Optionally Start Grafana

```bash
docker-compose up -d grafana

# Grafana will be available at http://localhost:3000
# Default credentials: admin/admin
```

## Verification

### Check Data Pipeline

```bash
# 1. Verify Kafka topics exist
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Expected topics:
# - gpu-metrics-raw
# - gpu-metrics-validated
# - gpu-metrics-enriched
# - gpu-metrics-invalid

# 2. Check data in Kafka (validated metrics)
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic gpu-metrics-validated \
  --from-beginning \
  --max-messages 1 | jq .

# 3. Verify database has data
docker-compose exec timescaledb psql -U gpu_monitor -d gpu_health -c \
  "SELECT COUNT(*) as metric_count FROM gpu_metrics;"

# Should show growing count (6 per minute = ~360 per hour)

# 4. Check health scores
docker-compose exec timescaledb psql -U gpu_monitor -d gpu_health -c \
  "SELECT time, overall_score, health_grade FROM gpu_health_scores ORDER BY time DESC LIMIT 5;"
```

### Test API Endpoints

```bash
# List active GPUs
curl http://localhost:8000/api/v1/gpus | jq .

# Get recent metrics for GPU
curl "http://localhost:8000/api/v1/gpus/GPU-abc123def456/metrics?hours=1" | jq . | head -30

# Get health scores
curl "http://localhost:8000/api/v1/gpus/GPU-abc123def456/health" | jq .

# Get fleet summary
curl http://localhost:8000/api/v1/fleet/summary | jq .

# Get statistical summary
curl "http://localhost:8000/api/v1/gpus/GPU-abc123def456/stats?hours=1" | jq .

# Check for alerts
curl http://localhost:8000/api/v1/alerts | jq .

# View API documentation (in browser)
# http://localhost:8000/docs
```

### Monitor Logs

```bash
# View all logs
docker-compose logs -f

# Specific service logs
docker-compose logs -f collector
docker-compose logs -f validator
docker-compose logs -f enricher
docker-compose logs -f timescale-sink
docker-compose logs -f health-scorer
docker-compose logs -f api

# Check for errors
docker-compose logs | grep -i error
```

## Expected Behavior

After 5-10 minutes of running, you should see:

### Mock DCGM
- Simulating 5-minute workload cycles
- Temperature: 50-85°C (varies with simulated workload)
- Power: 200-400W
- Utilization: 10-90%

### Database
- ~360 metric samples per hour
- Growing `gpu_metrics` table
- Health scores updated every 15 minutes
- Compression kicking in after 1 hour

### Health Scores
- Overall score: 85-95 (excellent/good range)
- All dimension scores calculated
- Occasional degradation factors based on simulated conditions

### API
- All endpoints returning data
- Sub-second response times
- OpenAPI docs at http://localhost:8000/docs

## Explore the Data

### Database Queries

```bash
docker-compose exec timescaledb psql -U gpu_monitor -d gpu_health
```

```sql
-- Latest metrics for all GPUs
SELECT * FROM v_latest_gpu_metrics;

-- Fleet summary
SELECT * FROM v_fleet_health_summary;

-- Temperature trend (1-minute buckets)
SELECT 
    time_bucket('1 minute', time) AS bucket,
    AVG(gpu_temp) AS avg_temp,
    MAX(gpu_temp) AS max_temp,
    MIN(gpu_temp) AS min_temp
FROM gpu_metrics
WHERE time > NOW() - INTERVAL '1 hour'
GROUP BY bucket
ORDER BY bucket DESC
LIMIT 20;

-- Throttling events
SELECT 
    time,
    gpu_temp,
    power_usage,
    throttle_reasons
FROM gpu_metrics
WHERE throttle_reasons > 0
ORDER BY time DESC
LIMIT 10;

-- Health score trend
SELECT 
    time,
    overall_score,
    health_grade,
    thermal_health,
    power_health
FROM gpu_health_scores
ORDER BY time DESC
LIMIT 10;

-- ECC error history
SELECT 
    time,
    ecc_sbe_volatile,
    ecc_dbe_volatile,
    ecc_sbe_aggregate,
    ecc_dbe_aggregate
FROM gpu_metrics
WHERE ecc_sbe_volatile > 0 OR ecc_dbe_volatile > 0
ORDER BY time DESC
LIMIT 20;
```

## Component Status Summary

```bash
# Quick status check of all services
docker-compose ps

# Should show all services "Up":
# - zookeeper
# - kafka
# - timescaledb
# - mock-dcgm
# - collector
# - validator
# - enricher
# - timescale-sink
# - health-scorer
# - api
# - grafana (if started)
```

## Stopping the System

```bash
# Stop all services
docker-compose down

# Stop and remove all data (CAUTION: deletes all metrics)
docker-compose down -v
```

## Troubleshooting

### No data in database

1. Check collector is running: `docker-compose logs collector`
2. Check Kafka has data: See verification steps above
3. Check sink is consuming: `docker-compose logs timescale-sink`
4. Restart sink: `docker-compose restart timescale-sink`

### Health scores not appearing

1. Wait 15 minutes (default scoring interval)
2. Check health-scorer logs: `docker-compose logs health-scorer`
3. Verify metrics exist: `SELECT COUNT(*) FROM gpu_metrics;`
4. Force scoring cycle: `docker-compose restart health-scorer`

### API errors

1. Check database connection: `curl http://localhost:8000/health`
2. View API logs: `docker-compose logs api`
3. Restart API: `docker-compose restart api`

### Services won't start

1. Check ports aren't in use: `lsof -i :9092` (Kafka), `:5432` (PostgreSQL)
2. Check Docker resources: Ensure 8GB+ RAM allocated
3. View service logs: `docker-compose logs <service-name>`
4. Rebuild: `docker-compose build <service-name>`

## Next Steps

Once the system is running:

1. **Explore Grafana** (http://localhost:3000)
   - Add TimescaleDB datasource: `timescaledb:5432`
   - Create dashboards for GPU metrics
   - Set up alert rules

2. **Customize Configuration**
   - Edit `docker-compose.yml` environment variables
   - Adjust scoring intervals, retention policies
   - Add more mock GPUs

3. **Implement Additional Features**
   - ML failure prediction models
   - Aggregator processor (1-min, 15-min windows)
   - Economic decision engine
   - Alert notifications

4. **Scale Testing**
   - Add multiple mock DCGM instances
   - Test with higher data volumes
   - Benchmark query performance

## Architecture Overview

```
┌──────────────┐
│  Mock DCGM   │  Simulates A100 GPU metrics (10s interval)
│   :9400      │
└──────┬───────┘
       │
       ▼ HTTP GET /metrics
┌──────────────┐
│  Collector   │  Scrapes and publishes to Kafka
└──────┬───────┘
       │
       ▼ Kafka: gpu-metrics-raw
┌──────────────┐
│  Validator   │  Schema + range validation
└──────┬───────┘
       │
       ▼ Kafka: gpu-metrics-validated
┌──────────────┐
│  Enricher    │  Join with asset metadata
└──────┬───────┘
       │
       ▼ Kafka: gpu-metrics-enriched
┌──────────────┐
│    Sink      │  Batch write to TimescaleDB
└──────┬───────┘
       │
       ▼
┌──────────────┐      ┌──────────────┐
│ TimescaleDB  │◄─────│ Health       │
│              │      │ Scorer       │
│ - gpu_metrics│      │ (15min)      │
│ - gpu_health │      └──────────────┘
│   _scores    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  FastAPI     │  Query interface (:8000)
│  + Grafana   │  Visualization (:3000)
└──────────────┘
```

## Support

- Documentation: `README_LOCAL_DEPLOYMENT.md`
- Architecture docs: `docs/architecture/`
- Issues: Check logs and troubleshooting section above

Enjoy exploring the GPU Health Monitor! 🚀
