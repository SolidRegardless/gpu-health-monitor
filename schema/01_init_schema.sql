-- GPU Health Monitor Database Schema
-- TimescaleDB Initialization Script

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- =========================
-- Core Tables
-- =========================

-- GPU Assets (regular table)
CREATE TABLE IF NOT EXISTS gpu_assets (
    gpu_uuid TEXT PRIMARY KEY,
    
    -- Hardware info
    model TEXT NOT NULL,
    architecture TEXT,
    compute_capability TEXT,
    memory_gb INT,
    
    -- Deployment info
    hostname TEXT,
    pci_bus_id TEXT,
    rack_id TEXT,
    cluster_id TEXT,
    datacenter TEXT,
    region TEXT,
    
    -- Asset lifecycle
    purchase_date DATE,
    deployment_date DATE DEFAULT CURRENT_DATE,
    warranty_expiry DATE,
    expected_eol DATE,
    
    -- SLA tier
    sla_tier TEXT DEFAULT 'development',
    priority INT DEFAULT 5,
    
    -- Metadata
    tags JSONB,
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_gpu_assets_hostname ON gpu_assets (hostname);
CREATE INDEX idx_gpu_assets_cluster ON gpu_assets (cluster_id);
CREATE INDEX idx_gpu_assets_tags ON gpu_assets USING GIN (tags);

-- Insert mock GPU asset
INSERT INTO gpu_assets (gpu_uuid, model, architecture, compute_capability, memory_gb, hostname, cluster_id, datacenter, tags)
VALUES (
    'GPU-abc123def456',
    'NVIDIA A100-SXM4-80GB',
    'Ampere',
    '8.0',
    80,
    'mock-gpu-node',
    'local-development',
    'local',
    '{"environment": "development", "mock": true}'::jsonb
) ON CONFLICT (gpu_uuid) DO NOTHING;

-- =========================
-- Time-Series Tables
-- =========================

-- Raw GPU Metrics (hypertable)
CREATE TABLE IF NOT EXISTS gpu_metrics (
    time TIMESTAMPTZ NOT NULL,
    gpu_uuid TEXT NOT NULL,
    hostname TEXT NOT NULL,
    
    -- GPU identification
    pci_bus_id TEXT,
    device_index SMALLINT,
    
    -- Health metrics
    gpu_temp REAL,
    memory_temp REAL,
    power_usage REAL,
    throttle_reasons BIGINT,
    
    -- Memory metrics
    fb_used_bytes BIGINT,
    fb_free_bytes BIGINT,
    fb_total_bytes BIGINT,
    memory_utilization REAL,
    ecc_sbe_volatile INT,
    ecc_dbe_volatile INT,
    ecc_sbe_aggregate BIGINT,
    ecc_dbe_aggregate BIGINT,
    retired_pages_sbe INT,
    retired_pages_dbe INT,
    
    -- Performance metrics
    sm_active REAL,
    sm_occupancy REAL,
    tensor_active REAL,
    dram_active REAL,
    pcie_tx_bytes_per_sec REAL,
    pcie_rx_bytes_per_sec REAL,
    
    -- Clock metrics
    sm_clock_mhz INT,
    mem_clock_mhz INT,
    
    -- Utilization
    gpu_utilization REAL,
    mem_copy_utilization REAL,
    
    -- Quality metadata
    collection_latency_ms INT,
    validation_passed BOOLEAN DEFAULT true,
    
    PRIMARY KEY (time, gpu_uuid)
);

-- Create hypertable (1-day chunks)
SELECT create_hypertable(
    'gpu_metrics',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_gpu_metrics_uuid_time ON gpu_metrics (gpu_uuid, time DESC);
CREATE INDEX IF NOT EXISTS idx_gpu_metrics_hostname_time ON gpu_metrics (hostname, time DESC);
CREATE INDEX IF NOT EXISTS idx_gpu_metrics_throttle ON gpu_metrics (time DESC) WHERE throttle_reasons > 0;
CREATE INDEX IF NOT EXISTS idx_gpu_metrics_ecc_errors ON gpu_metrics (time DESC) WHERE ecc_dbe_volatile > 0 OR ecc_sbe_volatile > 100;

-- Compression policy (compress chunks older than 1 hour for development)
ALTER TABLE gpu_metrics SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'gpu_uuid, hostname',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('gpu_metrics', INTERVAL '1 hour', if_not_exists => TRUE);

-- Retention policy (drop chunks older than 7 days for development)
SELECT add_retention_policy('gpu_metrics', INTERVAL '7 days', if_not_exists => TRUE);

-- =========================
-- Aggregated Metrics Tables
-- =========================

-- 1-Minute Aggregates
CREATE TABLE IF NOT EXISTS gpu_metrics_1min (
    time TIMESTAMPTZ NOT NULL,
    gpu_uuid TEXT NOT NULL,
    hostname TEXT NOT NULL,
    
    -- Temperature aggregates
    gpu_temp_avg REAL,
    gpu_temp_min REAL,
    gpu_temp_max REAL,
    gpu_temp_stddev REAL,
    
    memory_temp_avg REAL,
    memory_temp_max REAL,
    
    -- Power aggregates
    power_usage_avg REAL,
    power_usage_min REAL,
    power_usage_max REAL,
    
    -- Performance aggregates
    sm_active_avg REAL,
    sm_occupancy_avg REAL,
    tensor_active_avg REAL,
    
    pcie_tx_mbps_avg REAL,
    pcie_rx_mbps_avg REAL,
    
    -- Error counts
    ecc_sbe_count INT,
    ecc_dbe_count INT,
    
    -- Throttle events
    throttle_events INT,
    
    -- Sample metadata
    sample_count INT,
    
    PRIMARY KEY (time, gpu_uuid)
);

SELECT create_hypertable(
    'gpu_metrics_1min',
    'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

ALTER TABLE gpu_metrics_1min SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'gpu_uuid, hostname'
);

SELECT add_compression_policy('gpu_metrics_1min', INTERVAL '1 day', if_not_exists => TRUE);
SELECT add_retention_policy('gpu_metrics_1min', INTERVAL '30 days', if_not_exists => TRUE);

-- =========================
-- Health Score Tables
-- =========================

-- GPU Health Scores
CREATE TABLE IF NOT EXISTS gpu_health_scores (
    time TIMESTAMPTZ NOT NULL,
    gpu_uuid TEXT NOT NULL,
    
    -- Overall health score (0-100)
    overall_score REAL NOT NULL,
    health_grade TEXT,
    
    -- Dimension scores (0-100 each)
    memory_health REAL,
    thermal_health REAL,
    performance_health REAL,
    power_health REAL,
    reliability_health REAL,
    
    -- Trends
    score_delta_7d REAL,
    score_delta_30d REAL,
    degradation_rate REAL,
    
    -- Contributing factors
    degradation_factors JSONB,
    
    -- Scoring metadata
    scoring_version TEXT,
    scored_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (time, gpu_uuid)
);

SELECT create_hypertable(
    'gpu_health_scores',
    'time',
    chunk_time_interval => INTERVAL '30 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_health_scores_score ON gpu_health_scores (time DESC, overall_score ASC);
CREATE INDEX IF NOT EXISTS idx_health_scores_grade ON gpu_health_scores (time DESC, health_grade);

-- =========================
-- Failure Prediction Tables
-- =========================

-- GPU Failure Predictions
CREATE TABLE IF NOT EXISTS gpu_failure_predictions (
    time TIMESTAMPTZ NOT NULL,
    gpu_uuid TEXT NOT NULL,
    
    -- Failure probability (0.0 - 1.0)
    failure_prob_7d REAL,
    failure_prob_30d REAL,
    failure_prob_90d REAL,
    
    -- Predicted failure type
    predicted_failure_type TEXT,
    
    -- Time to failure estimate
    estimated_ttf_days INT,
    
    -- Model metadata
    model_name TEXT,
    model_version TEXT,
    confidence REAL,
    
    -- Features used
    feature_importance JSONB,
    
    predicted_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (time, gpu_uuid)
);

SELECT create_hypertable(
    'gpu_failure_predictions',
    'time',
    chunk_time_interval => INTERVAL '30 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_predictions_high_risk ON gpu_failure_predictions (time DESC)
    WHERE failure_prob_30d > 0.2;

-- =========================
-- Functions and Triggers
-- =========================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for gpu_assets
CREATE TRIGGER update_gpu_assets_updated_at
    BEFORE UPDATE ON gpu_assets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =========================
-- Views
-- =========================

-- Latest metrics view
CREATE OR REPLACE VIEW v_latest_gpu_metrics AS
SELECT DISTINCT ON (gpu_uuid)
    time,
    gpu_uuid,
    hostname,
    gpu_temp,
    memory_temp,
    power_usage,
    throttle_reasons,
    memory_utilization,
    sm_active,
    ecc_dbe_volatile,
    ecc_sbe_volatile
FROM gpu_metrics
ORDER BY gpu_uuid, time DESC;

-- Fleet health summary view
CREATE OR REPLACE VIEW v_fleet_health_summary AS
SELECT
    COUNT(DISTINCT gpu_uuid) AS total_gpus,
    AVG(gpu_temp) AS avg_temp,
    MAX(gpu_temp) AS max_temp,
    AVG(power_usage) AS avg_power,
    SUM(CASE WHEN throttle_reasons > 0 THEN 1 ELSE 0 END) AS throttling_count,
    SUM(CASE WHEN ecc_dbe_volatile > 0 THEN 1 ELSE 0 END) AS dbe_error_count
FROM v_latest_gpu_metrics;

-- =========================
-- Grants
-- =========================

-- Grant permissions to gpu_monitor user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gpu_monitor;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gpu_monitor;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO gpu_monitor;

-- Grant usage on schema
GRANT USAGE, CREATE ON SCHEMA public TO gpu_monitor;

-- Default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO gpu_monitor;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO gpu_monitor;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO gpu_monitor;

COMMIT;
