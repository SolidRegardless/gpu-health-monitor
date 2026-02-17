-- ============================================================
-- Demo seed: Grafana market intelligence commentary
-- Three sections displayed in the Secondary Market dashboard.
--
-- Safe to re-run: deletes previous seeded rows (model_used
-- starts with 'seeded-') and re-inserts fresh ones.
-- ============================================================

DELETE FROM gpu_market_commentary WHERE model_used LIKE 'seeded-%';

INSERT INTO gpu_market_commentary (generated_at, section, content, model_used)
VALUES

(NOW(), 'market_dynamics',
'A100 SXM4-80GB units are trading at $8,500 on the secondary market — a 43% discount to new-unit cost — as hyperscalers rotate Ampere capacity out ahead of Blackwell deployments. H100 SXM5-80GB holds firmer at $24,000 (75% of original), underpinned by persistent inference demand and constrained CoWoS supply. The $15,500 spread between the two architectures reflects the FP8 tensor-core premium the market is pricing in for H100 — a gap likely to narrow as GB200 availability improves in H2 2026.',
'seeded-v3'),

(NOW(), 'fleet_analysis',
'Current fleet health presents a mixed but actionable picture: 4 GPUs are flagged KEEP (health 81–96/100), 4 for SELL (health 58–66/100), and 2 for REPURPOSE (health 69–73/100). The KEEP cohort — two H100s in DC-EAST-01 and two A100s in UK-SOUTH-01 — shows NPV Keep exceeding market value by $3,800–$6,700 per unit, confirming continued deployment is economically optimal. The 4 SELL candidates (health below 67/100, failure probability 42–55%) represent $56,025 in recoverable secondary-market value that depreciates with each quarter of delay.',
'seeded-v3'),

(NOW(), 'forward_view',
'Over the next 3–6 months, A100 pricing is expected to soften toward $6,500–$7,500 as enterprise buyers gain Blackwell alternatives and hyperscaler offloading accelerates. H100 values should remain supported above $20,000 through mid-2026 while CoWoS packaging remains a supply constraint. Key actions: (1) execute SELL orders on the 4 flagged units within 60 days to capture current bid-side liquidity; (2) route the 2 REPURPOSE candidates to inference-serving workloads where reduced clock tolerance absorbs their instability profiles; (3) reassess the KEEP cohort at 90 days — any health score drop below 80/100 should trigger an immediate sell evaluation.',
'seeded-v3');
