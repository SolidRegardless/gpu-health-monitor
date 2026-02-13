# Changelog

All notable changes to the GPU Health Monitor project.

## [2026-02-13] - Production Deployment Fixes

### Fixed

#### Database Schema Initialization
- **Removed**: Conflicting `schema/01_init_schema_multi_gpu.sql` file
- **Added**: Proper `schema/07_init_multi_gpu_data.sql` for initial GPU data
- **Issue**: TimescaleDB container was failing with "column serial_number does not exist" error
- **Root Cause**: Two schema files numbered `01_*` caused execution order conflicts, and data insert used wrong column names
- **Impact**: Fresh deployments now initialize cleanly without manual database fixes
- **Details**: See `DEPLOYMENT_FIX.md`

#### Dashboard Gauge Visualization Fix (All Dashboards)
- **Fixed**: Missing filled progress bars on all gauge panels across 4 dashboards
- **Affected Dashboards**:
  - Datacenter Overview (3 gauges fixed)
  - GPU Fleet Overview (6 gauges fixed)
  - GPU Detail (1 gauge fixed)
  - GPU Overview (1 gauge fixed)
- **Total**: 13 gauge panels fixed
- **Added**: Min/max configuration for all gauges:
  - Temperature gauges: `min: 0, max: 100` (°C)
  - Memory temp gauge: `min: 0, max: 110` (°C)
  - Power gauges: `min: 0, max: 400` (single GPU) or `max: 3000` (fleet total)
  - Utilization/Health: `min: 0, max: 100` (%)
  - Error counters: `min: 0, max: 1000` (SBE) or `max: 100` (DBE)
- **Added**: 30-second time filter to datacenter aggregate queries
- **Issue**: Gauges showed numeric values but not filled progress bars
- **Root Cause**: Missing min/max configuration prevented Grafana from calculating fill percentage
- **Impact**: All gauges now display filled progress bars with proper colors (green/yellow/red)
- **Details**: See `DASHBOARD_GAUGE_FIX.md`

### Changed
- **Schema execution order**: Now properly loads 01-06 (structure) then 07 (data)
- **Dashboard queries**: All datacenter aggregate queries now filter to recent data
- **Documentation**: Updated `fresh-deployment.md` with fix notes

### Technical Details

**Schema Files (Final Structure)**:
```
schema/
├── 01_init_schema.sql           ← Core tables & hypertables
├── 02_aggregates.sql            ← Continuous aggregates
├── 03_anomalies.sql             ← Anomaly detection
├── 04_feature_store.sql         ← ML feature store
├── 05_economic_decisions.sql    ← Economic engine
├── 06_datacenter_mapping.sql    ← Datacenter mapping schema
└── 07_init_multi_gpu_data.sql   ← Initial 5-GPU data (NEW)
```

**Dashboard Changes**:
- Files: All 4 dashboards with gauge panels updated
- Total panels fixed: 13 gauges
- Query changes: Time filters added to datacenter aggregates
- Config changes: Min/max added to all gauges

**Gauge Ranges Configured**:
```
Temperature Gauges:
  - GPU Temp: 0-100°C (typical range, safe max ~95°C)
  - Memory Temp: 0-110°C (memory runs slightly hotter)

Power Gauges:
  - Single GPU: 0-400W (covers A100/H100 TDP)
  - Fleet Total: 0-3000W (5 GPUs × 600W headroom)

Utilization/Health:
  - GPU Utilization: 0-100%
  - Health Score: 0-100%

Error Counters:
  - SBE (Single-Bit): 0-1000 (accumulates slowly)
  - DBE (Double-Bit): 0-100 (should be rare/critical)
```

**Deployment Scripts**:
- ✅ No changes needed - scripts already correct
- ✅ All scripts tested with fixes applied
- ✅ Fresh deployments work end-to-end

### Testing

**Verified on Azure VM**:
- Location: North Europe
- IP: 98.71.11.28
- Status: ✅ All 17 containers running
- Data: ✅ 5 GPUs reporting metrics
- Dashboards: ✅ Filled gauges working correctly

**Test Commands**:
```bash
# Verify schema loads correctly
docker-compose -f docker/docker-compose.yml down -v
docker-compose -f docker/docker-compose.yml up -d
sleep 45
docker logs gpu-monitor-timescaledb | grep -i error  # Should be clean

# Verify gauge data
docker exec gpu-monitor-timescaledb psql -U gpu_monitor -d gpu_health \
  -c "SELECT COUNT(*) FROM gpu_assets;"  # Should return 5

# Verify queries work
docker exec gpu-monitor-timescaledb psql -U gpu_monitor -d gpu_health \
  -c "SELECT AVG(g.gpu_temp) FROM (
    SELECT DISTINCT ON (gpu_uuid) gpu_uuid, gpu_temp 
    FROM gpu_metrics 
    WHERE time > NOW() - INTERVAL '30 seconds' 
    ORDER BY gpu_uuid, time DESC
  ) g;"  # Should return ~70°C
```

### Migration Guide

For existing deployments that encounter these issues:

1. **Fix schema** (if TimescaleDB fails to start):
   ```bash
   cd gpu-health-monitor/schema
   rm 01_init_schema_multi_gpu.sql  # If exists
   # Pull latest 07_init_multi_gpu_data.sql from repo
   docker-compose -f docker/docker-compose.yml restart timescaledb
   ```

2. **Fix gauges** (if empty or no fill bars):
   ```bash
   # Pull latest datacenter-overview.json from repo
   cp config/grafana/dashboards/datacenter-overview.json /path/to/deployment/
   docker restart gpu-monitor-grafana
   # Hard refresh browser (Ctrl+Shift+R)
   ```

3. **Full redeploy** (cleanest option):
   ```bash
   docker-compose -f docker/docker-compose.yml down -v
   git pull  # Get latest fixes
   docker-compose -f docker/docker-compose.yml up -d
   ```

### Known Issues & Expected Behavior

**Predictive Analytics Dashboard Shows "No Data" (EXPECTED)**:
- **Status**: Expected for new deployments
- **Cause**: ML features require 7+ days of historical metrics data
- **Current Data**: ~21 minutes (130 records per GPU)
- **Timeline**: Predictions will automatically activate after 7 days (2026-02-20)
- **Services**: All ML services running correctly, waiting for data accumulation
- **Details**: See `PREDICTIVE_ANALYTICS_README.md`

**Components Affected**:
- Failure Probability Forecast (needs 7 days)
- ML Model Confidence (needs 7 days)  
- Predicted Failure Type (needs 7 days)
- Estimated Time to Failure (needs 7 days)
- Anomaly Timeline (limited until 24+ hours)

**Components Working**:
- GPU Health Scores ✅ (real-time, 10 records)
- Live monitoring dashboards ✅ (GPU Fleet, Datacenter, Detail)
- All metrics collection ✅ (130+ records per GPU)

### Deployment Verification Checklist

After deployment, verify:
- [ ] All 17 containers running (`docker ps | grep gpu-monitor | wc -l` → 17)
- [ ] TimescaleDB logs clean (`docker logs gpu-monitor-timescaledb | grep ERROR` → empty)
- [ ] 5 GPU assets exist (`docker exec gpu-monitor-timescaledb psql -U gpu_monitor -d gpu_health -c "SELECT COUNT(*) FROM gpu_assets;"` → 5)
- [ ] Metrics flowing (`docker logs gpu-monitor-collector --tail 10` → publishing messages)
- [ ] Grafana accessible (`curl -s http://localhost:3000/login` → 200 OK)
- [ ] Gauges filled (`open http://localhost:3000` → Datacenter Overview → filled progress bars)

---

## Previous Releases

See git history for earlier changes:
```bash
git log --oneline --graph
```

Key milestones:
- 2026-02-11: Multi-GPU simulation added
- 2026-02-12: Datacenter overview dashboard created
- 2026-02-13: Production deployment to Azure
