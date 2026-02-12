-- Feature Store for ML Models
-- Stores pre-computed features for training and inference

-- Feature metadata table
CREATE TABLE IF NOT EXISTS feature_definitions (
    feature_name TEXT PRIMARY KEY,
    feature_type TEXT NOT NULL, -- 'numeric', 'categorical', 'boolean'
    description TEXT,
    computation_logic TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Feature values (offline store)
CREATE TABLE IF NOT EXISTS gpu_features (
    time TIMESTAMPTZ NOT NULL,
    gpu_uuid TEXT NOT NULL,
    
    -- Statistical features (7-day rolling windows)
    gpu_temp_mean REAL,
    gpu_temp_std REAL,
    gpu_temp_min REAL,
    gpu_temp_max REAL,
    gpu_temp_trend REAL, -- Linear trend coefficient
    
    power_usage_mean REAL,
    power_usage_std REAL,
    power_usage_cv REAL, -- Coefficient of variation
    power_efficiency REAL, -- Performance per watt
    
    sm_active_mean REAL,
    sm_active_std REAL,
    sm_occupancy_mean REAL,
    
    memory_util_mean REAL,
    memory_util_std REAL,
    
    -- Event counts (last 7 days)
    thermal_throttle_count INT,
    power_brake_count INT,
    sw_power_cap_count INT,
    ecc_sbe_event_count INT,
    ecc_dbe_event_count INT,
    
    -- Anomaly features
    temp_spike_count INT, -- Temp > mean + 2*std
    power_anomaly_count INT,
    throttle_duration_hours REAL,
    
    -- Metadata features
    gpu_age_days INT,
    warranty_remaining_days INT,
    total_operating_hours REAL,
    
    -- Model identifiers
    model_a100 BOOLEAN,
    model_h100 BOOLEAN,
    
    -- Feature engineering metadata
    feature_version TEXT DEFAULT '1.0',
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (time, gpu_uuid)
);

-- Create hypertable
SELECT create_hypertable(
    'gpu_features',
    'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_gpu_features_uuid_time ON gpu_features (gpu_uuid, time DESC);
CREATE INDEX IF NOT EXISTS idx_gpu_features_computed_at ON gpu_features (computed_at DESC);

-- Compression
ALTER TABLE gpu_features SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'gpu_uuid',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('gpu_features', INTERVAL '7 days', if_not_exists => TRUE);

-- Retention policy (keep features for 1 year)
SELECT add_retention_policy('gpu_features', INTERVAL '365 days', if_not_exists => TRUE);

-- Training labels table (for supervised learning)
CREATE TABLE IF NOT EXISTS gpu_failure_labels (
    gpu_uuid TEXT NOT NULL,
    failure_date TIMESTAMPTZ NOT NULL,
    failure_type TEXT NOT NULL, -- 'memory', 'thermal', 'power', 'other'
    days_before_failure INT NOT NULL, -- Target: 7, 30, 90
    failure_confirmed BOOLEAN DEFAULT true,
    failure_description TEXT,
    root_cause TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    
    PRIMARY KEY (gpu_uuid, failure_date)
);

CREATE INDEX IF NOT EXISTS idx_failure_labels_date ON gpu_failure_labels (failure_date DESC);
CREATE INDEX IF NOT EXISTS idx_failure_labels_type ON gpu_failure_labels (failure_type);

-- Grant permissions
GRANT ALL ON feature_definitions TO gpu_monitor;
GRANT ALL ON gpu_features TO gpu_monitor;
GRANT ALL ON gpu_failure_labels TO gpu_monitor;

-- Insert feature definitions (documentation)
INSERT INTO feature_definitions (feature_name, feature_type, description) VALUES
    ('gpu_temp_mean', 'numeric', '7-day mean GPU temperature (°C)'),
    ('gpu_temp_std', 'numeric', '7-day std dev GPU temperature'),
    ('gpu_temp_trend', 'numeric', 'Linear regression slope of temperature over 7 days'),
    ('power_usage_mean', 'numeric', '7-day mean power usage (W)'),
    ('power_usage_cv', 'numeric', 'Coefficient of variation of power usage'),
    ('thermal_throttle_count', 'numeric', 'Count of thermal throttle events in 7 days'),
    ('ecc_dbe_event_count', 'numeric', 'Count of double-bit ECC error events'),
    ('gpu_age_days', 'numeric', 'Days since GPU deployment'),
    ('model_a100', 'boolean', 'Is NVIDIA A100 model'),
    ('model_h100', 'boolean', 'Is NVIDIA H100 model')
ON CONFLICT (feature_name) DO NOTHING;
