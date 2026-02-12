# GPU Health Monitor - Local Implementation Summary

## What Was Created

I've implemented a complete local deployment of the GPU Health Monitor system with a mock DCGM that simulates realistic GPU metrics. This allows you to test the entire pipeline without real GPU hardware.

### Components Implemented

#### 1. Mock DCGM Exporter (`src/mock-dcgm/`)
- **Purpose**: Simulates NVIDIA DCGM metrics in Prometheus format
- **Features**:
  - Realistic A100 GPU simulation
  - Workload patterns: 5-minute cycles (idle → ramp-up → peak → ramp-down)
  - Temperature: 50-95°C based on workload
  - Power: 50-400W based on workload
  - ECC errors: Occasional SBE, rare DBE
  - Throttling: Simulated thermal/power throttling
  - Memory: 10-90% utilization
- **Endpoint**: `http://localhost:9400/metrics`

#### 2. Metrics Collector (`src/collector/`)
- **Purpose**: Scrapes mock DCGM and publishes to Kafka
- **Features**:
  - Parses Prometheus format metrics
  - Enriches with metadata (cluster, datacenter, rack)
  - Publishes JSON events to Kafka
  - Automatic reconnection on failures
- **Interval**: 10 seconds

#### 3. TimescaleDB Sink (`src/processors/`)
- **Purpose**: Consumes Kafka events and writes to TimescaleDB
- **Features**:
  - Batch processing (configurable size/timeout)
  - Automatic schema mapping
  - Error handling and reconnection
  - ON CONFLICT handling for idempotency

#### 4. Database Schema (`schema/01_init_schema.sql`)
- **Hypertables**: gpu_metrics, gpu_metrics_1min, gpu_health_scores, gpu_failure_predictions
- **Compression**: After 1 hour (configurable)
- **Retention**: 7 days (configurable)
- **Indexes**: Optimized for time-series queries
- **Views**: Latest metrics, fleet summary

#### 5. Infrastructure (`docker/docker-compose.yml`)
- **Services**: Zookeeper, Kafka, TimescaleDB, Grafana, Mock DCGM, Collector, Sink, API, Health Scorer
- **Networks**: Isolated bridge network
- **Volumes**: Persistent data for Kafka, TimescaleDB, Grafana

## Quick Start

### 1. Start the System

```bash
cd /home/hart/.openclaw/workspace/gpu-health-monitor/docker

# Start core infrastructure
docker-compose up -d zookeeper kafka timescaledb

# Wait 30 seconds for initialization
sleep 30

# Start mock DCGM and collector
docker-compose up -d mock-dcgm collector

# Wait 10 seconds
sleep 10

# Start the sink processor
docker-compose up -d timescale-sink
```

### 2. Verify It's Working

**Check mock DCGM is generating metrics:**
```bash
curl http://localhost:9400/metrics | head -20
```

**Check Kafka has data:**
```bash
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic gpu-metrics-raw \
  --from-beginning \
  --max-messages 1 | jq .
```

**Check database has data:**
```bash
docker-compose exec timescaledb psql -U gpu_monitor -d gpu_health -c \
  "SELECT COUNT(*) FROM gpu_metrics;"

# Should see growing count of rows
```

### 3. Query the Data

```bash
# Connect to database
docker-compose exec timescaledb psql -U gpu_monitor -d gpu_health

# Run queries:
SELECT * FROM v_latest_gpu_metrics;

SELECT time, gpu_temp, power_usage, sm_active 
FROM gpu_metrics 
WHERE time > NOW() - INTERVAL '5 minutes'
ORDER BY time DESC 
LIMIT 10;

# Temperature over time
SELECT time_bucket('1 minute', time) AS bucket,
       AVG(gpu_temp) AS avg_temp,
       MAX(gpu_temp) AS max_temp
FROM gpu_metrics
WHERE time > NOW() - INTERVAL '1 hour'
GROUP BY bucket
ORDER BY bucket DESC;
```

### 4. Monitor Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f collector
docker-compose logs -f timescale-sink
docker-compose logs -f mock-dcgm
```

## Architecture Flow

```
┌─────────────┐    HTTP     ┌─────────────┐    Kafka      ┌─────────────┐
│  Mock DCGM  │─────────────>│  Collector  │──────────────>│    Kafka    │
│  :9400      │  /metrics   │             │  gpu-metrics  │             │
│             │  (10s poll) │             │     -raw      │             │
└─────────────┘             └─────────────┘               └──────┬──────┘
                                                                  │
                                                                  │ Consume
                                                                  │
                                                           ┌──────▼──────┐
                                                           │ Timescale   │
                                                           │    Sink     │
                                                           └──────┬──────┘
                                                                  │
                                                                  │ Batch Write
                                                                  │
                                                           ┌──────▼──────┐
                                                           │ TimescaleDB │
                                                           │   :5432     │
                                                           │             │
                                                           └─────────────┘
```

## Data Flow Example

1. **Mock DCGM** generates metrics every 10 seconds
2. **Collector** scrapes metrics, parses, enriches, publishes to Kafka
3. **Kafka** stores events in `gpu-metrics-raw` topic
4. **Sink** consumes events, batches, writes to TimescaleDB
5. **TimescaleDB** stores metrics in compressed hypertable

## Expected Data

After 5 minutes of running, you should have:
- ~30 metric samples in `gpu_metrics` table
- Data showing workload pattern (idle → busy → idle)
- Temperature rising and falling with workload
- Power usage correlating with temperature
- SM active percentage showing utilization

## Mock DCGM Behavior

The mock simulates a 5-minute workload cycle:

- **0-60s**: Idle (10% utilization, ~65°C, ~300W)
- **60-120s**: Ramp-up (10% → 90% utilization)
- **120-240s**: Peak workload (90% utilization, ~80°C, ~400W)
- **240-300s**: Ramp-down (90% → 10% utilization)
- **300s+**: Cycle repeats

This creates realistic patterns for testing health scoring and anomaly detection.

## Troubleshooting

### No Data in Kafka

```bash
# Check collector logs
docker-compose logs collector

# Check if mock DCGM is accessible
docker-compose exec collector curl http://mock-dcgm:9400/metrics
```

### No Data in Database

```bash
# Check sink logs
docker-compose logs timescale-sink

# Verify Kafka has data
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic gpu-metrics-raw \
  --from-beginning \
  --max-messages 5
```

### Services Won't Start

```bash
# Check service status
docker-compose ps

# Check specific service logs
docker-compose logs <service-name>

# Rebuild if needed
docker-compose build <service-name>
docker-compose up -d <service-name>
```

## Next Steps

### Immediate
1. Verify the basic pipeline is working
2. Check that metrics are flowing into TimescaleDB
3. Query the data and verify patterns

### Short Term
1. Implement stream processors (validator, enricher, aggregator)
2. Implement health scorer
3. Create Grafana dashboards
4. Build FastAPI endpoints

### Medium Term
1. Add more mock GPUs (multi-GPU simulation)
2. Implement ML models for failure prediction
3. Add alerting
4. Create economic decision engine

## File Structure

```
gpu-health-monitor/
├── docker/
│   └── docker-compose.yml          # Service orchestration
├── src/
│   ├── mock-dcgm/
│   │   ├── Dockerfile
│   │   └── mock_dcgm.py           # Mock DCGM exporter
│   ├── collector/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── collector.py           # Metrics collector
│   └── processors/
│       ├── Dockerfile.sink
│       ├── requirements.txt
│       └── timescale_sink.py      # Kafka → TimescaleDB
├── schema/
│   └── 01_init_schema.sql         # Database initialization
├── docs/
│   └── architecture/              # Architecture docs
└── README_LOCAL_DEPLOYMENT.md     # Detailed instructions
```

## Stopping the System

```bash
# Stop all services
docker-compose down

# Stop and remove all data
docker-compose down -v
```

## Configuration

Key environment variables (in `docker-compose.yml`):

- `COLLECTION_INTERVAL`: How often collector scrapes (default: 10s)
- `POLL_INTERVAL`: How often mock DCGM updates (default: 10s)
- `BATCH_SIZE`: Sink batch size (default: 100)
- `BATCH_TIMEOUT`: Max time to wait for batch (default: 5s)

## Performance

Current setup can handle:
- 1 GPU at 10s intervals: 6 events/minute = ~8,640 events/day
- Compressed storage: ~50 bytes/event compressed = ~430 KB/day
- 7-day retention: ~3 MB total

Scales linearly with number of GPUs.

## Support

For issues:
1. Check logs: `docker-compose logs <service>`
2. Review README_LOCAL_DEPLOYMENT.md
3. Check architecture docs in `docs/architecture/`

## Commit Details

**Commit**: 27479a3
**Date**: 2026-02-11
**Files**: 15 new files, 1,791 insertions
