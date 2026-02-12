-- Multi-GPU Asset Initialization
-- Adds 5 GPUs with different profiles for testing

INSERT INTO gpu_assets (gpu_uuid, hostname, model, serial_number, pci_bus_id, deployment_date, warranty_expiry, location, tags)
VALUES
    -- GPU 0: Healthy, 6 months old
    ('GPU-abc123def456', 'collector', 'NVIDIA A100-SXM4-80GB', 'SN-A100-001', '0000:00:00.0',
     NOW() - INTERVAL '6 months', NOW() + INTERVAL '30 months', 'datacenter-1-rack-a',
     '{"profile": "healthy", "purpose": "ml-training", "tier": "production"}'::jsonb),
    
    -- GPU 1: Runs hot, 18 months old
    ('GPU-def456abc789', 'collector', 'NVIDIA A100-SXM4-80GB', 'SN-A100-002', '0000:01:00.0',
     NOW() - INTERVAL '18 months', NOW() + INTERVAL '18 months', 'datacenter-1-rack-a',
     '{"profile": "high_temp", "purpose": "ml-training", "tier": "production", "issues": "runs-hot"}'::jsonb),
    
    -- GPU 2: H100, power hungry, 3 months old
    ('GPU-ghi789jkl012', 'collector', 'NVIDIA H100-SXM5-80GB', 'SN-H100-001', '0000:02:00.0',
     NOW() - INTERVAL '3 months', NOW() + INTERVAL '33 months', 'datacenter-1-rack-b',
     '{"profile": "power_hungry", "purpose": "llm-inference", "tier": "production"}'::jsonb),
    
    -- GPU 3: Aging, 36 months old, higher ECC errors
    ('GPU-mno345pqr678', 'collector', 'NVIDIA A100-SXM4-80GB', 'SN-A100-003', '0000:03:00.0',
     NOW() - INTERVAL '36 months', NOW() - INTERVAL '6 months', 'datacenter-1-rack-c',
     '{"profile": "aging", "purpose": "dev-testing", "tier": "secondary", "issues": "ecc-errors"}'::jsonb),
    
    -- GPU 4: H100, excellent condition, 1 month old
    ('GPU-stu901vwx234', 'collector', 'NVIDIA H100-SXM5-80GB', 'SN-H100-002', '0000:04:00.0',
     NOW() - INTERVAL '1 month', NOW() + INTERVAL '35 months', 'datacenter-1-rack-b',
     '{"profile": "excellent", "purpose": "llm-training", "tier": "premium"}'::jsonb)
ON CONFLICT (gpu_uuid) DO UPDATE SET
    hostname = EXCLUDED.hostname,
    model = EXCLUDED.model,
    tags = EXCLUDED.tags;

-- Verify insertion
SELECT gpu_uuid, model, tags->>'profile' as profile, 
       EXTRACT(MONTH FROM (NOW() - deployment_date)) as age_months
FROM gpu_assets
ORDER BY gpu_uuid;
