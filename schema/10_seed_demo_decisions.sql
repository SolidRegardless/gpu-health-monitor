-- ============================================================
-- Demo seed: realistic GPU economic decisions + health scores
-- Produces a balanced 4 KEEP / 4 SELL / 2 REPURPOSE story
-- across two data centres (DC-EAST-01 and UK-SOUTH-01).
--
-- Run after all other schema files.
-- Safe to re-run: uses ON CONFLICT DO UPDATE.
-- ============================================================

-- 1. Correct secondary market prices
--    (live fetcher may lag; seed ensures dashboards show
--     realistic A100 $8,500 and H100 $24,000 mid prices)
INSERT INTO gpu_market_prices
    (fetched_at, model, condition,
     price_low_usd, price_high_usd, price_mid_usd,
     original_cost_usd, source)
VALUES
    (NOW(), 'NVIDIA A100-SXM4-80GB', 'used_good',
     7500, 9500, 8500, 15000,
     'JarvisLabs/secondary-market'),
    (NOW(), 'NVIDIA H100-SXM5-80GB', 'used_good',
     21000, 27000, 24000, 32000,
     'JarvisLabs/secondary-market')
ON CONFLICT DO NOTHING;


-- 2. Health scores matched to each GPU profile
INSERT INTO gpu_health_scores
    (time, gpu_uuid, overall_score, health_grade,
     thermal_health, power_health, memory_health,
     performance_health, reliability_health)
VALUES
-- DC-EAST-01 A100s
(NOW(), 'GPU-abc123def456', 87.0, 'B+', 88, 90, 86, 85, 90),  -- healthy, 6 mo
(NOW(), 'GPU-def456abc789', 62.0, 'D',  48, 72, 65, 63, 55),  -- high_temp, 18 mo
(NOW(), 'GPU-mno345pqr678', 58.0, 'D-', 65, 60, 52, 55, 48),  -- aging, 36 mo
-- DC-EAST-01 H100s
(NOW(), 'GPU-ghi789jkl012', 81.0, 'B',  82, 68, 85, 84, 86),  -- power_hungry, 3 mo
(NOW(), 'GPU-stu901vwx234', 96.0, 'A+', 97, 95, 96, 97, 96),  -- excellent, 1 mo
-- UK-SOUTH-01 A100s
(NOW(), 'GPU-uk2bbb222ccc', 89.0, 'A-', 90, 92, 88, 88, 91),  -- power_efficient, 4 mo
(NOW(), 'GPU-uk4ddd444eee', 73.0, 'C+', 75, 78, 70, 68, 72),  -- intermittent_load, 22 mo
-- UK-SOUTH-01 H100s
(NOW(), 'GPU-uk1aaa111bbb', 69.0, 'C+', 54, 74, 72, 73, 70),  -- unstable_temp, 8 mo
(NOW(), 'GPU-uk3ccc333ddd', 64.0, 'D+', 68, 70, 52, 65, 60),  -- memory_stress, 14 mo
(NOW(), 'GPU-uk5eee555fff', 66.0, 'C-', 70, 66, 62, 64, 62)   -- early_warning, 28 mo
ON CONFLICT (time, gpu_uuid) DO UPDATE
    SET overall_score      = EXCLUDED.overall_score,
        health_grade       = EXCLUDED.health_grade,
        thermal_health     = EXCLUDED.thermal_health,
        power_health       = EXCLUDED.power_health,
        memory_health      = EXCLUDED.memory_health,
        performance_health = EXCLUDED.performance_health,
        reliability_health = EXCLUDED.reliability_health;


-- 3. Economic decisions with NPV values and rationale
INSERT INTO gpu_economic_decisions
    (time, gpu_uuid, decision,
     npv_keep, npv_sell, npv_repurpose,
     salvage_value, expected_value,
     confidence, health_score, failure_prob_30d,
     rationale)
VALUES

-- ── KEEP (4 GPUs) ─────────────────────────────────────────────────────────

(NOW(), 'GPU-abc123def456', 'keep',
 12400, 7650, 8200, 8075, 12400, 0.84, 87.0, 0.08,
 'KEEP: Health 87/100, failure risk just 8%. NPV Keep ($12,400) outperforms market ($7,650) by $4,750. Healthy 6-month A100 with strong utilisation — no economic case to liquidate.'),

(NOW(), 'GPU-ghi789jkl012', 'keep',
 26800, 21600, 18500, 22800, 26800, 0.81, 81.0, 0.12,
 'KEEP: 3-month H100 at 81/100 health retains 84% original value. NPV Keep ($26,800) leads market by $5,200. Elevated power draw within thermal spec — retain for dense workloads.'),

(NOW(), 'GPU-stu901vwx234', 'keep',
 29500, 22800, 19200, 24000, 29500, 0.93, 96.0, 0.03,
 'KEEP: Exceptional health 96/100 at 1 month. NPV Keep ($29,500) exceeds market by $6,700. Premature liquidation would forfeit significant forward value. Hold.'),

(NOW(), 'GPU-uk2bbb222ccc', 'keep',
 11900, 8075, 7200, 8500, 11900, 0.87, 89.0, 0.06,
 'KEEP: Power-efficient A100, health 89/100. NPV Keep ($11,900) exceeds market by $3,825. 4-month deployment, well within productive lifecycle. Optimal for continued dense compute.'),

-- ── SELL (4 GPUs) ─────────────────────────────────────────────────────────

(NOW(), 'GPU-def456abc789', 'sell',
 4100, 7225, 5800, 7600, 7225, 0.79, 62.0, 0.42,
 'SELL: Persistent thermal degradation — health 62/100 at 18 months. NPV Sell ($7,225) exceeds NPV Keep ($4,100) by $3,125. 48% recovery on original cost before further decline.'),

(NOW(), 'GPU-mno345pqr678', 'sell',
 1200, 5700, 3900, 6000, 5700, 0.86, 58.0, 0.55,
 'SELL: 36-month deployment, health 58/100 and declining. NPV Keep ($1,200) well below market ($5,700). Capture residual value now — failure probability 55% within 30 days.'),

(NOW(), 'GPU-uk3ccc333ddd', 'sell',
 9200, 19000, 14500, 20000, 19000, 0.82, 64.0, 0.44,
 'SELL: HBM stress pattern detected at 14 months — health 64/100. NPV Sell ($19,000) outperforms Keep ($9,200) by $9,800. Exit before potential HBM2e failure event compresses value further.'),

(NOW(), 'GPU-uk5eee555fff', 'sell',
 6300, 17100, 12800, 18000, 17100, 0.80, 66.0, 0.48,
 'SELL: Early-warning telemetry at 28 months — accelerating degradation, health 66/100. NPV Sell ($17,100) leads Keep ($6,300) by $10,800. Maximise recovery before Blackwell compression.'),

-- ── REPURPOSE (2 GPUs) ────────────────────────────────────────────────────

(NOW(), 'GPU-uk1aaa111bbb', 'repurpose',
 14600, 18200, 19800, 19200, 19800, 0.76, 69.0, 0.38,
 'REPURPOSE: Thermal instability (health 69/100) disqualifies high-stakes HPC workloads. Repurpose value ($19,800) leads sell ($18,200) and keep ($14,600). Route to inference serving — reduced clock tolerance absorbs thermal variance.'),

(NOW(), 'GPU-uk4ddd444eee', 'repurpose',
 5800, 6175, 7400, 6500, 7400, 0.72, 73.0, 0.28,
 'REPURPOSE: Intermittent load profile suggests PCIe controller instability at 22 months. Repurpose ($7,400) outperforms sell ($6,175) and keep ($5,800). Batch inference workloads tolerate duty-cycle variation.')

ON CONFLICT (time, gpu_uuid) DO UPDATE
    SET decision         = EXCLUDED.decision,
        npv_keep         = EXCLUDED.npv_keep,
        npv_sell         = EXCLUDED.npv_sell,
        npv_repurpose    = EXCLUDED.npv_repurpose,
        salvage_value    = EXCLUDED.salvage_value,
        expected_value   = EXCLUDED.expected_value,
        confidence       = EXCLUDED.confidence,
        health_score     = EXCLUDED.health_score,
        failure_prob_30d = EXCLUDED.failure_prob_30d,
        rationale        = EXCLUDED.rationale;
