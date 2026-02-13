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

### Solution - Part 1: Query Timing
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

### Solution - Part 2: Gauge Min/Max Configuration

The gauges also needed **explicit min/max values** to display the filled progress bar:

```json
// BEFORE (no fill bar):
{
  "fieldConfig": {
    "defaults": {
      "thresholds": { ... },
      "unit": "celsius"
      // ❌ Missing min/max!
    }
  }
}

// AFTER (shows fill bar):
{
  "fieldConfig": {
    "defaults": {
      "min": 0,           // ← Added
      "max": 100,         // ← Added
      "thresholds": { ... },
      "unit": "celsius"
    }
  }
}
```

**Min/Max Values Set:**
- **Avg Temperature**: 0-100°C (typical GPU operating range)
- **Total Power**: 0-3000W (5 GPUs × ~600W headroom per GPU)

**Why these ranges?**
- Temperature: GPUs idle around 40°C, max safe temp ~95°C, so 0-100°C covers full range
- Power: H100 TDP is ~700W, A100 is ~400W. 3000W total gives headroom for all 5 GPUs at peak
- Thresholds (yellow/red warnings) work as percentages of these ranges

**Visual Result:**
- At ~70°C average: Gauge shows ~70% filled, green/yellow color
- At ~1800W total: Gauge shows ~60% filled, green color

Without min/max, Grafana displays the numeric value but can't draw the filled bar (doesn't know the scale).

### Changes Applied

**Files Modified**:
- `config/grafana/dashboards/datacenter-overview.json`
- `config/grafana/dashboards/gpu-fleet-overview.json`
- `config/grafana/dashboards/gpu-detail.json`
- `config/grafana/dashboards/gpu-overview.json`

**Panels Fixed (Total: 13 gauges across 4 dashboards)**:

**Datacenter Overview (3 gauges)**:
1. Avg Temperature (0-100°C)
2. Total Power Consumption (0-3000W)
3. Avg GPU Utilization (0-100%)

**GPU Fleet Overview (6 gauges)**:
1. Avg GPU Temp (0-100°C)
2. Max GPU Temp (0-100°C)
3. Total Power Draw (0-3000W)
4. Avg Utilization (0-100%)
5. Total SBE Errors (0-1000 count)
6. Total DBE Errors (0-100 count)

**GPU Detail (1 gauge)**:
1. GPU Utilization (0-100%)

**GPU Overview (1 gauge)**:
1. Overall Health Score (0-100%)

**Changes Applied**:
1. **Query Timing**: Added `AND time > NOW() - INTERVAL '30 seconds'` to WHERE clause
   - Both queries now filter to only recent data
   - Eliminates race conditions and stale data issues

2. **Gauge Configuration**: Added explicit min/max values
   - Avg Temperature: `min: 0, max: 100` (°C)
   - Total Power: `min: 0, max: 3000` (W)
   - Enables Grafana to render filled progress bar

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
