-- Economic Decision Engine Table
-- Stores lifecycle recommendations based on NPV analysis

CREATE TABLE IF NOT EXISTS gpu_economic_decisions (
    time TIMESTAMPTZ NOT NULL,
    gpu_uuid TEXT NOT NULL,
    
    -- Decision
    decision TEXT NOT NULL,  -- 'keep', 'sell', 'repurpose', 'decommission'
    
    -- NPV calculations (USD)
    npv_keep REAL,
    npv_sell REAL,
    npv_repurpose REAL,
    salvage_value REAL,
    expected_value REAL,  -- NPV of chosen decision
    
    -- Confidence and rationale
    confidence REAL,  -- 0.0 - 1.0
    rationale TEXT,
    
    -- Input data (for audit trail)
    health_score REAL,
    failure_prob_30d REAL,
    utilization REAL,
    
    -- Metadata
    analyzed_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (time, gpu_uuid)
);

-- Create hypertable
SELECT create_hypertable(
    'gpu_economic_decisions',
    'time',
    chunk_time_interval => INTERVAL '30 days',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_economic_decisions_decision ON gpu_economic_decisions (decision, time DESC);
CREATE INDEX IF NOT EXISTS idx_economic_decisions_value ON gpu_economic_decisions (expected_value DESC, time DESC);
CREATE INDEX IF NOT EXISTS idx_economic_decisions_confidence ON gpu_economic_decisions (confidence DESC);

-- Retention policy (keep decisions for 2 years)
SELECT add_retention_policy('gpu_economic_decisions', INTERVAL '730 days', if_not_exists => TRUE);

-- Grant permissions
GRANT ALL ON gpu_economic_decisions TO gpu_monitor;

-- Create a view for latest decisions
-- Exposes npv_keep, npv_sell, npv_repurpose so dashboards and the
-- market-intelligence API can query them directly without joining
-- the full hypertable.
CREATE OR REPLACE VIEW v_latest_economic_decisions AS
SELECT DISTINCT ON (gpu_uuid)
    time,
    gpu_uuid,
    decision,
    npv_keep,
    npv_sell,
    npv_repurpose,
    expected_value,
    confidence,
    rationale,
    health_score,
    failure_prob_30d
FROM gpu_economic_decisions
ORDER BY gpu_uuid, time DESC;

GRANT SELECT ON v_latest_economic_decisions TO gpu_monitor;
