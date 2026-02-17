-- Secondary Market GPU Prices Table
-- Tracks real-time secondary market pricing for GPU models
-- Used to compare operational NPV vs liquidation value

CREATE TABLE IF NOT EXISTS gpu_market_prices (
    fetched_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model              TEXT NOT NULL,                          -- e.g. 'NVIDIA A100-SXM4-80GB'
    condition          TEXT NOT NULL DEFAULT 'used_good',      -- 'used_good', 'refurb', 'new'
    price_low_usd      NUMERIC(10,2),
    price_high_usd     NUMERIC(10,2),
    price_mid_usd      NUMERIC(10,2),                         -- average / midpoint
    original_cost_usd  NUMERIC(10,2),                         -- original new-market purchase price
    source             TEXT,                                   -- e.g. 'jarvislabs', 'web_scrape', 'manual', 'seed'
    PRIMARY KEY (fetched_at, model, condition)
);

-- Convert to TimescaleDB hypertable (partitioned by fetched_at)
SELECT create_hypertable(
    'gpu_market_prices',
    'fetched_at',
    if_not_exists => TRUE,
    migrate_data   => TRUE
);

-- Index for efficient latest-price lookups
CREATE INDEX IF NOT EXISTS idx_gpu_market_prices_model_condition
    ON gpu_market_prices (model, condition, fetched_at DESC);

-- Grant access to application user
GRANT ALL ON gpu_market_prices TO gpu_monitor;

-- ─── Seed data (realistic 2026 secondary-market values) ──────────────────────

-- NVIDIA A100 SXM4-80GB  (used_good)
-- Source: JarvisLabs AI FAQs, eBay, ServerMonkey — Jan 2026 survey
INSERT INTO gpu_market_prices
    (fetched_at, model, condition, price_low_usd, price_high_usd, price_mid_usd, original_cost_usd, source)
VALUES
    (NOW() - INTERVAL '1 hour',
     'NVIDIA A100-SXM4-80GB',
     'used_good',
     7000.00,
     10000.00,
     8500.00,
     15000.00,
     'seed')
ON CONFLICT DO NOTHING;

-- NVIDIA H100 SXM5-80GB  (used_good)
-- Source: JarvisLabs blog, Vast.ai listings — Jan 2026 survey
INSERT INTO gpu_market_prices
    (fetched_at, model, condition, price_low_usd, price_high_usd, price_mid_usd, original_cost_usd, source)
VALUES
    (NOW() - INTERVAL '1 hour',
     'NVIDIA H100-SXM5-80GB',
     'used_good',
     22000.00,
     28000.00,
     24000.00,
     32000.00,
     'seed')
ON CONFLICT DO NOTHING;

-- ─── View: latest price per model + condition ─────────────────────────────────

CREATE OR REPLACE VIEW v_latest_market_prices AS
SELECT DISTINCT ON (model, condition)
    fetched_at,
    model,
    condition,
    price_low_usd,
    price_high_usd,
    price_mid_usd,
    original_cost_usd,
    source
FROM gpu_market_prices
ORDER BY model, condition, fetched_at DESC;

GRANT SELECT ON v_latest_market_prices TO gpu_monitor;
