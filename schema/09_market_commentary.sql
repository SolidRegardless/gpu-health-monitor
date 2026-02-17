-- AI-generated secondary market commentary
-- Written by market-price-fetcher service every 30 minutes
-- Read by Grafana text panel

CREATE TABLE IF NOT EXISTS gpu_market_commentary (
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    section      TEXT NOT NULL,  -- 'market_dynamics' | 'fleet_analysis' | 'forward_view'
    content      TEXT NOT NULL,
    model_used   TEXT,
    PRIMARY KEY (generated_at, section)
);

SELECT create_hypertable(
    'gpu_market_commentary', 'generated_at',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_commentary_section_time ON gpu_market_commentary (section, generated_at DESC);

-- Retention: keep 30 days of commentary
SELECT add_retention_policy('gpu_market_commentary', INTERVAL '30 days', if_not_exists => TRUE);

GRANT ALL ON gpu_market_commentary TO gpu_monitor;

-- View: latest commentary per section
CREATE OR REPLACE VIEW v_latest_market_commentary AS
SELECT DISTINCT ON (section)
    generated_at,
    section,
    content,
    model_used
FROM gpu_market_commentary
ORDER BY section, generated_at DESC;

GRANT SELECT ON v_latest_market_commentary TO gpu_monitor;
