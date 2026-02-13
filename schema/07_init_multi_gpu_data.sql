-- Multi-GPU Asset and Datacenter Initialization
-- Populates gpu_assets and gpu_datacenter_mapping with 5 test GPUs
-- This file runs AFTER schema creation (01-06)

-- Insert GPU asset metadata
INSERT INTO gpu_assets (gpu_uuid, hostname, model, pci_bus_id, deployment_date, warranty_expiry, datacenter, rack_id, tags)
VALUES
    -- GPU 0: Healthy baseline (A100, 6 months old)
    ('GPU-abc123def456', 'collector', 'NVIDIA A100-SXM4-80GB', '0000:00:00.0',
     NOW() - INTERVAL '6 months', NOW() + INTERVAL '30 months', 'DC-EAST-01', 'rack-A1',
     '{"profile": "healthy", "purpose": "ml-training", "tier": "production"}'::jsonb),
    
    -- GPU 1: Runs hot (A100, 18 months old, elevated temps)
    ('GPU-def456abc789', 'collector', 'NVIDIA A100-SXM4-80GB', '0000:01:00.0',
     NOW() - INTERVAL '18 months', NOW() + INTERVAL '18 months', 'DC-EAST-01', 'rack-A1',
     '{"profile": "high_temp", "purpose": "ml-training", "tier": "production", "issues": "runs-hot"}'::jsonb),
    
    -- GPU 2: Power hungry (H100, 3 months old, high power draw)
    ('GPU-ghi789jkl012', 'collector', 'NVIDIA H100-SXM5-80GB', '0000:02:00.0',
     NOW() - INTERVAL '3 months', NOW() + INTERVAL '33 months', 'DC-EAST-01', 'rack-A2',
     '{"profile": "power_hungry", "purpose": "llm-inference", "tier": "production"}'::jsonb),
    
    -- GPU 3: Aging hardware (A100, 36 months old, higher ECC error rate)
    ('GPU-mno345pqr678', 'collector', 'NVIDIA A100-SXM4-80GB', '0000:03:00.0',
     NOW() - INTERVAL '36 months', NOW() - INTERVAL '6 months', 'DC-EAST-01', 'rack-A2',
     '{"profile": "aging", "purpose": "dev-testing", "tier": "secondary", "issues": "ecc-errors"}'::jsonb),
    
    -- GPU 4: Excellent condition (H100, 1 month old, optimal performance)
    ('GPU-stu901vwx234', 'collector', 'NVIDIA H100-SXM5-80GB', '0000:04:00.0',
     NOW() - INTERVAL '1 month', NOW() + INTERVAL '35 months', 'DC-EAST-01', 'rack-A3',
     '{"profile": "excellent", "purpose": "llm-training", "tier": "premium"}'::jsonb)
ON CONFLICT (gpu_uuid) DO UPDATE SET
    hostname = EXCLUDED.hostname,
    model = EXCLUDED.model,
    tags = EXCLUDED.tags;

-- Insert datacenter mapping
INSERT INTO gpu_datacenter_mapping (gpu_uuid, datacenter, rack_id, location)
VALUES
    ('GPU-abc123def456', 'DC-EAST-01', 'rack-A1', 'US-East'),
    ('GPU-def456abc789', 'DC-EAST-01', 'rack-A1', 'US-East'),
    ('GPU-ghi789jkl012', 'DC-EAST-01', 'rack-A2', 'US-East'),
    ('GPU-mno345pqr678', 'DC-EAST-01', 'rack-A2', 'US-East'),
    ('GPU-stu901vwx234', 'DC-EAST-01', 'rack-A3', 'US-East')
ON CONFLICT (gpu_uuid) DO UPDATE SET
    datacenter = EXCLUDED.datacenter,
    rack_id = EXCLUDED.rack_id,
    location = EXCLUDED.location;

-- Verify insertion
SELECT 
    a.gpu_uuid, 
    a.model, 
    a.tags->>'profile' as profile,
    d.datacenter,
    d.rack_id,
    EXTRACT(MONTH FROM (NOW() - a.deployment_date))::int as age_months
FROM gpu_assets a
JOIN gpu_datacenter_mapping d ON a.gpu_uuid = d.gpu_uuid
ORDER BY a.gpu_uuid;
