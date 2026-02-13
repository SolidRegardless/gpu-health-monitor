# Dashboard Gauge Fix - Datacenter Overview

## Issue: Intermittent Empty Gauge Values

### Problem
On the **Datacenter Overview** dashboard, the gauge panels for **Avg Temperature** and **Total Power Consumption** sometimes stop showing filled values. The gauges would intermittently display empty/blank instead of the current metrics.

### Root Cause
The SQL queries for these gauges used `DISTINCT ON (gpu_uuid)` to get the latest reading for each GPU, but **did not include a time filter**:

```sql
-- PROBLEMATIC QUERY:
SELECT AVG(g.gpu_temp) as "Avg Temp"
FROM (
  SELECT DISTINCT ON (gpu_uuid) gpu_uuid, gpu_temp
  FROM gpu_metrics
  WHERE gpu_uuid IN (SELECT gpu_uuid FROM gpu_datacenter_mapping WHERE datacenter = '$datacenter')
  ORDER BY gpu_uuid, time DESC
) g
```

**Why this causes intermittent failures:**

1. **Race Condition**: Without a time constraint, the query scans the entire table. If data is being written at the moment the query runs, `DISTINCT ON` might pick up rows at different stages of transaction commit.

2. **Stale Data**: The query could return rows from minutes ago if newer data hasn't been fully indexed yet.

3. **Inconsistent Aggregation**: Different GPUs might have data from different time periods, causing the aggregate to be incorrect or empty.

4. **Query Performance**: Scanning the entire hypertable without a time filter is slower and more likely to timeout or return partial results.

### Solution
Added a **30-second time window** to ensure queries only aggregate over recent, consistent data:

```sql
-- FIXED QUERY:
SELECT AVG(g.gpu_temp) as "Avg Temp"
FROM (
  SELECT DISTINCT ON (gpu_uuid) gpu_uuid, gpu_temp
  FROM gpu_metrics
  WHERE gpu_uuid IN (SELECT gpu_uuid FROM gpu_datacenter_mapping WHERE datacenter = '$datacenter')
    AND time > NOW() - INTERVAL '30 seconds'  -- ← TIME FILTER ADDED
  ORDER BY gpu_uuid, time DESC
) g
```

**Why 30 seconds?**
- GPUs report metrics every ~10 seconds
- 30 seconds guarantees we always have at least 2-3 data points per GPU
- Recent enough to be "live" but wide enough to avoid gaps during write delays
- TimescaleDB hypertables are highly optimized for time-range queries

### Changes Applied

**File Modified**: `config/grafana/dashboards/datacenter-overview.json`

**Panels Fixed**:
1. **Avg Temperature** (gauge panel)
2. **Total Power Consumption** (gauge panel)

**Query Changes**:
- Added `AND time > NOW() - INTERVAL '30 seconds'` to WHERE clause
- Both queries now filter to only recent data
- Eliminates race conditions and stale data issues

### Testing

**Verify the fix works:**
```bash
# On Azure VM or local deployment:
docker exec gpu-monitor-timescaledb psql -U gpu_monitor -d gpu_health << EOF
-- Test the fixed query:
SELECT AVG(g.gpu_temp) as "Avg Temp"
FROM (
  SELECT DISTINCT ON (gpu_uuid) gpu_uuid, gpu_temp
  FROM gpu_metrics
  WHERE gpu_uuid IN (SELECT gpu_uuid FROM gpu_datacenter_mapping WHERE datacenter = 'DC-EAST-01')
    AND time > NOW() - INTERVAL '30 seconds'
  ORDER BY gpu_uuid, time DESC
) g;
EOF
```

**Expected Result**: Should always return a value (never NULL) as long as data is flowing.

### Deployment

1. **Local**: Dashboard JSON updated and committed to git
2. **Azure VM**: Fixed dashboard uploaded and Grafana restarted
3. **Verification**: Gauges should now consistently show values without intermittent blanks

### Prevention
For future dashboard queries on time-series data:

✅ **Always include a time filter** when querying `gpu_metrics`  
✅ Use time windows appropriate for data collection frequency (2-3x the reporting interval)  
✅ Test queries under load to catch race conditions  
✅ Prefer continuous aggregates (pre-computed) for gauges when possible  

---

**Status**: ✅ Fixed and deployed  
**Dashboards Affected**: Datacenter Overview  
**Panels Fixed**: Avg Temperature, Total Power Consumption  
**Date**: 2026-02-13
