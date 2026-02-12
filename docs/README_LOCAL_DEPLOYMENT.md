# GPU Health Monitor - Local Deployment

## Overview

This is a complete local implementation of the GPU Health Monitor system using a mock DCGM that simulates realistic GPU metrics for a single NVIDIA A100 GPU.

## Architecture

```
Mock DCGM → Collector → Kafka → Stream Processors → TimescaleDB → API/Grafana
```

### Components

- **Mock DCGM** - Simulates DCGM exporter with realistic GPU metrics
- **Collector** - Scrapes mock DCGM and publishes to Kafka  
- **Kafka** - Message queue for event streaming
- **Stream Processors** - Validate, enrich, and aggregate metrics
- **TimescaleDB** - Time-series database for metrics storage
- **Health Scorer** - Computes multi-dimensional health scores
- **API** - FastAPI service for queries
- **Grafana** - Visualization dashboards

## Prerequisites

- Docker and Docker Compose
- 8GB+ RAM available for containers
- Ports available: 2181, 9092, 9093, 5432, 3000, 8000, 9400

## Quick Start

### 1. Start Infrastructure

```bash
cd docker
docker-compose up -d zookeeper kafka timescaledb
```

Wait for services to be healthy (~30 seconds):

```bash
docker-compose ps
```

### 2. Verify Database Initialization

```bash
docker-compose logs timescaledb | grep "database system is ready"
```

### 3. Start Mock DCGM and Collector

```bash
docker-compose up -d mock-dcgm collector
```

### 4. Verify Data Flow

Check mock DCGM metrics:
```bash
curl http://localhost:9400/metrics
```

Check Kafka topics:
```bash
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

View raw metrics in Kafka:
```bash
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic gpu-metrics-raw \
  --from-beginning \
  --max-messages 1 | jq .
```

### 5. Start Stream Processors

```bash
# Note: These are TODO - implement as needed
# docker-compose up -d validator enricher timescale-sink
```

### 6. Query Database

```bash
docker-compose exec timescaledb psql -U gpu_monitor -d gpu_health -c "SELECT COUNT(*) FROM gpu_metrics;"
```

### 7. Start Additional Services

```bash
docker-compose up -d grafana health-scorer api
```

## Access Points

- **Mock DCGM Metrics**: http://localhost:9400/metrics
- **Grafana**: http://localhost:3000 (admin/admin)
- **API**: http://localhost:8000/docs
- **TimescaleDB**: localhost:5432 (gpu_monitor/gpu_monitor_secret)

## Development Workflow

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f collector
docker-compose logs -f mock-dcgm
```

### Restart a Service

```bash
docker-compose restart collector
```

### Rebuild After Code Changes

```bash
docker-compose build collector
docker-compose up -d collector
```

### Access Database

```bash
docker-compose exec timescaledb psql -U gpu_monitor -d gpu_health
```

Example queries:

```sql
-- Latest metrics
SELECT * FROM v_latest_gpu_metrics;

-- Fleet summary
SELECT * FROM v_fleet_health_summary;

-- Recent metrics
SELECT time, gpu_uuid, gpu_temp, power_usage, sm_active
FROM gpu_metrics
WHERE time > NOW() - INTERVAL '5 minutes'
ORDER BY time DESC
LIMIT 10;

-- Temperature over time
SELECT time_bucket('1 minute', time) AS bucket,
       AVG(gpu_temp) AS avg_temp,
       MAX(gpu_temp) AS max_temp
FROM gpu_metrics
WHERE time > NOW() - INTERVAL '1 hour'
GROUP BY bucket
ORDER BY bucket DESC;
```

## Mock DCGM Behavior

The mock DCGM simulates realistic GPU behavior:

- **Workload Patterns**: 5-minute cycles (idle → ramp-up → peak → ramp-down → idle)
- **Temperature**: 65°C base + workload heating (up to 80°C) + random variation
- **Power**: 300W base + workload power (up to 400W)
- **ECC Errors**: Occasional single-bit errors, rare double-bit errors
- **Throttling**: Simulated thermal/power throttling when limits exceeded
- **Memory**: 10-90% utilization based on workload

## Troubleshooting

### Kafka Connection Issues

```bash
# Check Kafka is running
docker-compose ps kafka

# Check Kafka logs
docker-compose logs kafka

# List topics (should work if Kafka is healthy)
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

### Database Connection Issues

```bash
# Check TimescaleDB is running
docker-compose ps timescaledb

# Check if database is ready
docker-compose exec timescaledb pg_isready -U gpu_monitor

# View database logs
docker-compose logs timescaledb
```

### Collector Not Publishing

```bash
# Check collector logs
docker-compose logs collector

# Verify mock DCGM is accessible from collector
docker-compose exec collector curl http://mock-dcgm:9400/metrics
```

### No Data in Database

```bash
# Check if data is in Kafka
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic gpu-metrics-raw \
  --from-beginning \
  --max-messages 5

# Check if sink processor is running (when implemented)
docker-compose ps timescale-sink
```

## Stopping the System

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clears all data)
docker-compose down -v
```

## Next Steps

1. Implement stream processors (validator, enricher, sink)
2. Implement health scorer
3. Create Grafana dashboards
4. Build API endpoints
5. Add alerting
6. Implement ML prediction models

## Directory Structure

```
.
├── docker/
│   └── docker-compose.yml      # Service orchestration
├── src/
│   ├── mock-dcgm/              # Mock DCGM exporter
│   ├── collector/              # Metrics collector
│   ├── processors/             # Stream processors
│   ├── health-scorer/          # Health scoring engine
│   └── api/                    # FastAPI service
├── schema/
│   └── 01_init_schema.sql      # Database schema
├── config/
│   └── grafana/                # Grafana dashboards
└── docs/
    └── architecture/           # Architecture documentation
```

## Configuration

Environment variables can be customized in `docker-compose.yml`:

- `COLLECTION_INTERVAL` - Metrics collection interval (default: 10s)
- `POLL_INTERVAL` - Mock DCGM update interval (default: 10s)
- `CLUSTER_NAME` - Cluster identifier
- `DATACENTER` - Datacenter identifier

## Performance Notes

- Mock DCGM updates every 10 seconds
- Collector publishes every 10 seconds
- Database compression after 1 hour
- Data retention: 7 days (configurable in schema)
- Kafka retention: 7 days

## Support

For questions or issues:
- Check the architecture docs in `docs/architecture/`
- Review component logs with `docker-compose logs`
- Open an issue on the GitHub repository

## License

See LICENSE file in project root.
