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

#### Datacenter Overview Dashboard Gauges
- **Fixed**: Intermittent empty values in Avg Temperature and Total Power Consumption gauges
- **Added**: 30-second time filter to queries (`AND time > NOW() - INTERVAL '30 seconds'`)
- **Added**: Min/max configuration for filled progress bars:
  - Avg Temperature: `min: 0, max: 100` (°C)
  - Total Power: `min: 0, max: 3000` (W)
- **Issue**: Gauges showed numbers but not filled bars, and sometimes showed blank values
- **Root Cause**: 
  1. Missing time filter caused race conditions during concurrent writes
  2. Missing min/max prevented Grafana from rendering fill bars
- **Impact**: Gauges now consistently show filled progress bars with proper colors
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
- File: `config/grafana/dashboards/datacenter-overview.json`
- Panels: Avg Temperature, Total Power Consumption
- Query: Added time filter for consistency
- Config: Added min/max for visual fill bars

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

### Known Issues

None - all major issues resolved.

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
