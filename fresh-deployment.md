# Fresh Deployment Guide

**Quick reference for deploying GPU Health Monitor on a fresh system**

> **🔧 Recent Fixes Applied (2026-02-13):**
> - **Schema initialization**: Removed conflicting `01_init_schema_multi_gpu.sql`, replaced with `07_init_multi_gpu_data.sql`
> - **Datacenter gauges**: Added min/max configuration (0-100°C, 0-3000W) for filled progress bars
> - **Query timing**: Added 30-second time filters to prevent empty gauge values
> - See `DEPLOYMENT_FIX.md` and `DASHBOARD_GAUGE_FIX.md` for technical details

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 8 GB RAM minimum
- 10 GB disk space
- Linux/macOS/Windows with WSL2

## 🚀 One-Command Deployment

```bash
cd gpu-health-monitor
docker-compose -f docker/docker-compose.yml up -d
```

Wait ~60 seconds for initialization, then access:
- **Grafana:** http://localhost:3000 (admin/admin)
- **TimescaleDB:** localhost:5432 (gpu_monitor/gpu_monitor_secret)
- **Mock DCGM:** http://localhost:9400/health

## 📋 Step-by-Step Deployment

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd gpu-health-monitor
```

### 2. Start Services

```bash
docker-compose -f docker/docker-compose.yml up -d
```

This starts 17 containers:
- TimescaleDB (database)
- Kafka + Zookeeper (streaming)
- Mock DCGM (GPU simulation)
- Collector (metrics scraper)
- Sink (Kafka → DB)
- Grafana (dashboards)
- Additional processing services

### 3. Verify Services

```bash
# Check all containers are running
docker ps | grep gpu-monitor

# Should show 17 containers in "Up" status
```

### 4. Verify Database

```bash
# Check TimescaleDB health
docker exec gpu-monitor-timescaledb pg_isready

# Connect to database
docker exec -it gpu-monitor-timescaledb psql -U gpu_monitor -d gpu_health

# Check tables
\dt

# Check GPU data is flowing
SELECT COUNT(*), COUNT(DISTINCT gpu_uuid) FROM gpu_metrics;

# Exit
\q
```

Expected output:
- 16 tables created
- 5 unique GPUs
- Metrics count increasing every 10 seconds

### 5. Access Grafana

1. Open browser: http://localhost:3000
2. Login: `admin` / `admin`
3. Skip password change (or set new password)
4. Navigate to **Dashboards** → **Browse**
5. You should see 6 dashboards:
   - Datacenter Overview
   - GPU Detail Dashboard
   - GPU Fleet Overview
   - GPU Health Monitor Overview
   - GPU Health Monitor - Simple
   - GPU Predictive Analytics & Failure Forecast

### 6. Verify Mock DCGM

```bash
# Check health
curl http://localhost:9400/health | jq

# Should return 5 GPUs with status "healthy"
```

### 7. Verify Data Pipeline

```bash
# Check collector logs (should show metrics being published)
docker logs gpu-monitor-collector --tail 10

# Check sink logs (should show writes to TimescaleDB)
docker logs gpu-monitor-timescale-sink --tail 10

# Both should show activity every 10 seconds
```

## 🎯 What Gets Auto-Provisioned

### Database Schema (7 SQL files executed in order):

1. **01_init_schema.sql** - Core tables (gpu_metrics, gpu_assets, etc.)
2. **02_aggregates.sql** - Continuous aggregates (1min, 5min, 1hour)
3. **03_anomalies.sql** - Anomaly detection tables
4. **04_feature_store.sql** - ML feature store
5. **05_economic_decisions.sql** - Economic engine tables
6. **06_datacenter_mapping.sql** - Datacenter mapping schema
7. **07_init_multi_gpu_data.sql** - Initial 5-GPU data (assets + datacenter mapping)

### Grafana Dashboards (6 auto-loaded):

All dashboards in `config/grafana/dashboards/` are automatically provisioned:
- ✅ Datasource pre-configured
- ✅ GPU selector dropdowns populated
- ✅ Time-series queries working
- ✅ Auto-refresh enabled

### Mock DCGM (5 GPUs):

Each GPU has a unique profile:
- **GPU-abc123def456** - Healthy baseline
- **GPU-def456abc789** - Runs hot
- **GPU-ghi789jkl012** - Power hungry (H100)
- **GPU-mno345pqr678** - Aging with ECC errors
- **GPU-stu901vwx234** - Excellent new GPU (H100)

## 🔍 Troubleshooting

### Services Won't Start

```bash
# Check logs for specific container
docker logs gpu-monitor-<service-name>

# Common issues:
# - Port conflicts (3000, 5432, 9092, 9400)
# - Insufficient memory
# - Docker daemon not running
```

### No Data in Grafana

```bash
# 1. Verify Mock DCGM is running
curl http://localhost:9400/health

# 2. Check collector is publishing
docker logs gpu-monitor-collector --tail 20

# 3. Check sink is writing
docker logs gpu-monitor-timescale-sink --tail 20

# 4. Check database has data
docker exec gpu-monitor-timescaledb psql -U gpu_monitor -d gpu_health -c "SELECT COUNT(*) FROM gpu_metrics;"
```

### Dashboards Show Errors

```bash
# Restart Grafana
docker restart gpu-monitor-grafana

# Wait 10 seconds
sleep 10

# Clear browser cache and refresh
```

### Database Connection Issues

```bash
# Check TimescaleDB is healthy
docker exec gpu-monitor-timescaledb pg_isready

# Check password
docker exec gpu-monitor-timescaledb psql -U gpu_monitor -d gpu_health -c "SELECT 1;"

# If fails, check environment variables in docker-compose.yml
```

## 🛑 Stopping the System

```bash
# Stop all services (keeps data)
docker-compose -f docker/docker-compose.yml stop

# Stop and remove containers (keeps data)
docker-compose -f docker/docker-compose.yml down

# Stop and remove ALL data (DESTRUCTIVE)
docker-compose -f docker/docker-compose.yml down -v
```

## 🔄 Restarting After Stop

```bash
# Start services
docker-compose -f docker/docker-compose.yml start

# Or bring up (if down)
docker-compose -f docker/docker-compose.yml up -d
```

Data persists in Docker volumes, so metrics history is preserved.

## 📊 Expected Behavior

### After 1 Minute:
- ✅ All containers running
- ✅ Database initialized with schema
- ✅ 5 GPU assets created
- ✅ Mock DCGM serving metrics
- ✅ Collector publishing to Kafka
- ✅ Sink writing to TimescaleDB
- ✅ ~30 metrics in database

### After 5 Minutes:
- ✅ ~150 metrics collected
- ✅ Grafana dashboards showing live data
- ✅ All gauges displaying values
- ✅ Time-series charts populating

### After 1 Hour:
- ✅ ~1,800 metrics collected
- ✅ Clear trends visible in charts
- ✅ ECC error accumulation visible
- ✅ Temperature variation patterns observable

## 🎓 Next Steps

1. **Explore Dashboards:**
   - Start with **GPU Fleet Overview** to see all GPUs
   - Use **GPU Detail Dashboard** to drill into specific GPUs
   - Check **Datacenter Overview** for rack-level aggregation

2. **Customize Configuration:**
   - Modify GPU profiles in `src/mock-dcgm/mock_dcgm_multi.py`
   - Add more datacenters in `schema/06_datacenter_mapping.sql`
   - Adjust retention policies in `schema/01_init_schema.sql`

3. **Scale Up:**
   - Add real DCGM exporters (replace mock-dcgm)
   - Configure multiple collectors for different clusters
   - Set up alert rules in Grafana

## 🆘 Support

Check documentation:
- `README.md` - Project overview
- `CURRENT_STATUS.md` - Implementation status
- `docs/DATABASE_TABLES_EXPLAINED.md` - Schema reference
- `gpu-health-system-architecture.md` - System design

Container logs:
```bash
# View logs for any service
docker logs gpu-monitor-<service> --tail 50 --follow
```

Database queries:
```bash
# Run any SQL query
docker exec -it gpu-monitor-timescaledb psql -U gpu_monitor -d gpu_health -c "YOUR_QUERY_HERE"
```

---

**System should be fully operational within 60 seconds of `docker-compose up -d`**
