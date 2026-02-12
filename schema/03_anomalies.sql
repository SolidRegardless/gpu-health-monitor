-- Anomalies table for ML-detected issues
CREATE TABLE IF NOT EXISTS anomalies (
    time TIMESTAMPTZ NOT NULL,
    gpu_uuid TEXT NOT NULL,
    anomaly_type TEXT NOT NULL,
    value REAL,
    z_score REAL,
    baseline_mean REAL,
    severity TEXT,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by TEXT,
    CONSTRAINT anomalies_pkey PRIMARY KEY (time, gpu_uuid, anomaly_type)
);

-- Create hypertable
SELECT create_hypertable('anomalies', 'time', if_not_exists => TRUE);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_anomalies_gpu ON anomalies (gpu_uuid, time DESC);
CREATE INDEX IF NOT EXISTS idx_anomalies_severity ON anomalies (severity, time DESC) WHERE NOT acknowledged;
CREATE INDEX IF NOT EXISTS idx_anomalies_type ON anomalies (anomaly_type, time DESC);

-- Retention policy: keep anomalies for 90 days
SELECT add_retention_policy('anomalies', INTERVAL '90 days', if_not_exists => TRUE);

GRANT SELECT, INSERT, UPDATE ON anomalies TO gpu_monitor;
