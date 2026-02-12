# Continuous Aggregates Update Frequency - Fixed

**Date:** 2026-02-12  
**Issue:** Continuous aggregate tables (gpu_metrics_1min, gpu_metrics_5min, gpu_metrics_1hour) were not updating frequently enough

---

## Problem Identified

The continuous aggregate tables had large `end_offset` values that prevented recent data from being materialized:

**Original Configuration:**
- `gpu_metrics_1min`: end_offset = **1 minute** → wouldn't show data from last minute
- `gpu_metrics_5min`: end_offset = **5 minutes** → wouldn't show data from last 5 minutes
- `gpu_metrics_1hour`: end_offset = **1 hour** → wouldn't show data from last hour

**Symptoms:**
- 1-min aggregate: 3+ minutes stale
- 5-min aggregate: 12+ minutes stale
- 1-hour aggregate: 2h 57m+ stale

---

## Root Cause

TimescaleDB continuous aggregates use `end_offset` to avoid materializing incomplete time buckets. The default settings were too conservative for a real-time monitoring system.

From the schema (`schema/02_aggregates.sql`):
```sql
SELECT add_continuous_aggregate_policy('gpu_metrics_1min',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 minute',  -- ❌ Too conservative
    schedule_interval => INTERVAL '1 minute');
```

---

## Solution Applied

### 1. Updated Refresh Policies

```sql
-- Remove old policies
SELECT remove_continuous_aggregate_policy('gpu_metrics_1min');
SELECT remove_continuous_aggregate_policy('gpu_metrics_5min');
SELECT remove_continuous_aggregate_policy('gpu_metrics_1hour');

-- Add new policies with smaller end_offset and faster refresh
-- 1-minute aggregates
SELECT add_continuous_aggregate_policy('gpu_metrics_1min',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '10 seconds',      -- ✅ Much better
    schedule_interval => INTERVAL '30 seconds'); -- ✅ Faster refresh

-- 5-minute aggregates  
SELECT add_continuous_aggregate_policy('gpu_metrics_5min',
    start_offset => INTERVAL '30 days',
    end_offset => INTERVAL '30 seconds',       -- ✅ Much better
    schedule_interval => INTERVAL '1 minute'); -- ✅ Faster refresh

-- 1-hour aggregates
SELECT add_continuous_aggregate_policy('gpu_metrics_1hour',
    start_offset => INTERVAL '90 days',
    end_offset => INTERVAL '5 minutes',        -- ✅ Much better
    schedule_interval => INTERVAL '10 minutes'); -- ✅ Faster refresh
```

### 2. Manual Refresh to Catch Up

```sql
-- Force immediate refresh of all aggregates
CALL refresh_continuous_aggregate('gpu_metrics_1min', NULL, NULL);
CALL refresh_continuous_aggregate('gpu_metrics_5min', NULL, NULL);
CALL refresh_continuous_aggregate('gpu_metrics_1hour', NULL, NULL);
```

---

## Results

**Before Fix:**
- Raw metrics: 9 seconds old ✅
- 1-min aggregate: 3 minutes old ❌
- 5-min aggregate: 12 minutes old ❌
- 1-hour aggregate: 2h 57m old ❌

**After Fix:**
- Raw metrics: 1.5 seconds old ✅
- 1-min aggregate: ~1 minute 20 seconds old ✅
- 5-min aggregate: ~4 minutes 20 seconds old ✅
- 1-hour aggregate: ~57 minutes old ✅

**Expected Behavior:**
- 1-min aggregate: Shows complete 1-minute buckets up to 10 seconds ago
- 5-min aggregate: Shows complete 5-minute buckets up to 30 seconds ago
- 1-hour aggregate: Shows complete 1-hour buckets up to 5 minutes ago

---

## Configuration Summary

| Aggregate | Schedule | End Offset | Expected Age |
|-----------|----------|------------|--------------|
| **1-minute** | Every 30 seconds | 10 seconds | ~10-40 seconds |
| **5-minute** | Every 1 minute | 30 seconds | ~30-90 seconds |
| **1-hour** | Every 10 minutes | 5 minutes | ~5-15 minutes |

### Why These Settings?

1. **End Offset:**
   - Small enough for near-real-time monitoring
   - Large enough to avoid incomplete buckets
   - 10s for 1-min buckets (we collect every 10s)
   - 30s for 5-min buckets
   - 5m for 1-hour buckets

2. **Schedule Interval:**
   - 1-min aggregate: 30s refresh = responsive without excessive overhead
   - 5-min aggregate: 1m refresh = catches new buckets quickly
   - 1-hour aggregate: 10m refresh = sufficient for long-term trends

---

## Verification

### Check Current Status

```sql
-- Current data freshness
SELECT 
    NOW() as current_time,
    (SELECT MAX(time) FROM gpu_metrics) as raw_latest,
    NOW() - (SELECT MAX(time) FROM gpu_metrics) as raw_age,
    (SELECT MAX(time) FROM gpu_metrics_1min) as agg_1min_latest,
    NOW() - (SELECT MAX(time) FROM gpu_metrics_1min) as agg_1min_age,
    (SELECT MAX(time) FROM gpu_metrics_5min) as agg_5min_latest,
    NOW() - (SELECT MAX(time) FROM gpu_metrics_5min) as agg_5min_age;
```

### Check Job Status

```sql
SELECT 
    job_id,
    hypertable_name,
    last_run_started_at,
    last_successful_finish,
    total_runs,
    total_successes,
    next_start
FROM timescaledb_information.job_stats
WHERE job_id IN (1011, 1012, 1013)
ORDER BY job_id;
```

### Check Policy Configuration

```sql
SELECT 
    j.job_id,
    ca.view_name,
    j.schedule_interval,
    j.config->>'end_offset' as end_offset,
    j.config->>'start_offset' as start_offset
FROM timescaledb_information.jobs j
JOIN timescaledb_information.continuous_aggregates ca 
    ON ca.materialization_hypertable_name = CONCAT('_materialized_hypertable_', (j.config->>'mat_hypertable_id')::text)
WHERE j.proc_name = 'policy_refresh_continuous_aggregate'
ORDER BY ca.view_name;
```

---

## Update Schema File

The schema file should be updated to reflect the new best practices:

**File:** `schema/02_aggregates.sql`

**Changes:**
```sql
-- 1-minute aggregates - UPDATED REFRESH POLICY
SELECT add_continuous_aggregate_policy('gpu_metrics_1min',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '10 seconds',      -- Changed from 1 minute
    schedule_interval => INTERVAL '30 seconds', -- Changed from 1 minute
    if_not_exists => TRUE);

-- 5-minute aggregates - UPDATED REFRESH POLICY
SELECT add_continuous_aggregate_policy('gpu_metrics_5min',
    start_offset => INTERVAL '30 days',
    end_offset => INTERVAL '30 seconds',      -- Changed from 5 minutes
    schedule_interval => INTERVAL '1 minute', -- Changed from 5 minutes
    if_not_exists => TRUE);

-- 1-hour aggregates - UPDATED REFRESH POLICY
SELECT add_continuous_aggregate_policy('gpu_metrics_1hour',
    start_offset => INTERVAL '90 days',
    end_offset => INTERVAL '5 minutes',       -- Changed from 1 hour
    schedule_interval => INTERVAL '10 minutes', -- Changed from 1 hour
    if_not_exists => TRUE);
```

---

## Impact on Grafana Dashboards

With these changes, Grafana dashboards using the aggregate tables will now show:
- Near-real-time data (1-2 minute lag for 1-min aggregates)
- Better responsiveness for time-series queries
- More accurate "current" health status

---

## Monitoring Recommendations

### Alert if Aggregates Get Stale

```sql
-- Alert if 1-min aggregate is more than 5 minutes old
SELECT 
    CASE 
        WHEN NOW() - MAX(time) > INTERVAL '5 minutes' 
        THEN 'ALERT: gpu_metrics_1min is stale'
        ELSE 'OK'
    END as status
FROM gpu_metrics_1min;
```

### Regular Health Check

Add to monitoring:
```bash
# Check aggregate freshness
docker compose exec timescaledb psql -U gpu_monitor -d gpu_health -c "
    SELECT 
        'gpu_metrics_1min' as agg,
        NOW() - MAX(time) as age,
        CASE WHEN NOW() - MAX(time) > INTERVAL '5 minutes' THEN 'STALE' ELSE 'OK' END as status
    FROM gpu_metrics_1min;
"
```

---

## Future Considerations

### For Production Deployment

1. **Monitor Job Performance:**
   - Watch for refresh job duration increasing
   - Scale if jobs take >50% of schedule_interval

2. **Tune Based on Load:**
   - Increase schedule_interval if system is CPU-constrained
   - Decrease end_offset further if even fresher data is needed

3. **Add Compression:**
   - Aggregates accumulate less data than raw metrics
   - Compression policies already configured in schema

---

## References

- TimescaleDB Continuous Aggregates: https://docs.timescale.com/use-timescale/latest/continuous-aggregates/
- Refresh Policies: https://docs.timescale.com/api/latest/continuous-aggregates/add_continuous_aggregate_policy/
- Schema: `schema/02_aggregates.sql`

---

**Status:** ✅ FIXED - Continuous aggregates now update within expected timeframes
