-- Continuous aggregates for automatic time-based rollups
-- These are materialized views that TimescaleDB keeps up-to-date automatically
--
-- IMPORTANT: If this script fails on gpu_metrics_1min, it may create a regular table
-- instead of a continuous aggregate. To fix:
--   DROP TABLE IF EXISTS gpu_metrics_1min CASCADE;
--   Then re-run this script.

-- Clean up any incorrectly created tables from previous failed runs
DROP TABLE IF EXISTS gpu_metrics_1min CASCADE;
DROP TABLE IF EXISTS gpu_metrics_5min CASCADE;
DROP TABLE IF EXISTS gpu_metrics_1hour CASCADE;

-- 1-minute aggregates
CREATE MATERIALIZED VIEW gpu_metrics_1min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS time,
    gpu_uuid,
    hostname,
    AVG(gpu_temp) as gpu_temp_avg,
    MAX(gpu_temp) as gpu_temp_max,
    MIN(gpu_temp) as gpu_temp_min,
    AVG(memory_temp) as memory_temp_avg,
    MAX(memory_temp) as memory_temp_max,
    AVG(power_usage) as power_usage_avg,
    MAX(power_usage) as power_usage_max,
    AVG(sm_active) as sm_active_avg,
    MAX(sm_active) as sm_active_max,
    AVG(memory_utilization) as memory_util_avg,
    MAX(memory_utilization) as memory_util_max,
    SUM(ecc_sbe_volatile) as ecc_sbe_count,
    SUM(ecc_dbe_volatile) as ecc_dbe_count,
    COUNT(*) as sample_count
FROM gpu_metrics
GROUP BY time_bucket('1 minute', time), gpu_uuid, hostname;

-- Enable automatic refresh policy (refresh every minute, keep last 7 days)
SELECT add_continuous_aggregate_policy('gpu_metrics_1min',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => TRUE);

-- 5-minute aggregates
CREATE MATERIALIZED VIEW gpu_metrics_5min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', time) AS time,
    gpu_uuid,
    hostname,
    AVG(gpu_temp) as gpu_temp_avg,
    MAX(gpu_temp) as gpu_temp_max,
    MIN(gpu_temp) as gpu_temp_min,
    AVG(memory_temp) as memory_temp_avg,
    MAX(memory_temp) as memory_temp_max,
    AVG(power_usage) as power_usage_avg,
    MAX(power_usage) as power_usage_max,
    MIN(power_usage) as power_usage_min,
    AVG(sm_active) as sm_active_avg,
    MAX(sm_active) as sm_active_max,
    AVG(memory_utilization) as memory_util_avg,
    MAX(memory_utilization) as memory_util_max,
    SUM(ecc_sbe_volatile) as ecc_sbe_count,
    SUM(ecc_dbe_volatile) as ecc_dbe_count,
    COUNT(*) as sample_count
FROM gpu_metrics
GROUP BY time_bucket('5 minutes', time), gpu_uuid, hostname;

-- Enable automatic refresh policy
SELECT add_continuous_aggregate_policy('gpu_metrics_5min',
    start_offset => INTERVAL '30 days',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => TRUE);

-- 1-hour aggregates
CREATE MATERIALIZED VIEW gpu_metrics_1hour
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS time,
    gpu_uuid,
    hostname,
    AVG(gpu_temp) as gpu_temp_avg,
    MAX(gpu_temp) as gpu_temp_max,
    MIN(gpu_temp) as gpu_temp_min,
    AVG(memory_temp) as memory_temp_avg,
    MAX(memory_temp) as memory_temp_max,
    AVG(power_usage) as power_usage_avg,
    MAX(power_usage) as power_usage_max,
    MIN(power_usage) as power_usage_min,
    AVG(sm_active) as sm_active_avg,
    MAX(sm_active) as sm_active_max,
    AVG(memory_utilization) as memory_util_avg,
    MAX(memory_utilization) as memory_util_max,
    SUM(ecc_sbe_volatile) as ecc_sbe_count,
    SUM(ecc_dbe_volatile) as ecc_dbe_count,
    COUNT(*) as sample_count
FROM gpu_metrics
GROUP BY time_bucket('1 hour', time), gpu_uuid, hostname;

-- Enable automatic refresh policy
SELECT add_continuous_aggregate_policy('gpu_metrics_1hour',
    start_offset => INTERVAL '90 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_metrics_1min_time_gpu ON gpu_metrics_1min (time DESC, gpu_uuid);
CREATE INDEX IF NOT EXISTS idx_metrics_5min_time_gpu ON gpu_metrics_5min (time DESC, gpu_uuid);
CREATE INDEX IF NOT EXISTS idx_metrics_1hour_time_gpu ON gpu_metrics_1hour (time DESC, gpu_uuid);

-- Grant permissions
GRANT SELECT ON gpu_metrics_1min TO gpu_monitor;
GRANT SELECT ON gpu_metrics_5min TO gpu_monitor;
GRANT SELECT ON gpu_metrics_1hour TO gpu_monitor;
