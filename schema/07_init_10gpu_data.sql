-- 10-GPU Multi-Datacenter Initialization
-- DC-EAST-01: 5 GPUs (original)
-- UK-SOUTH-01: 5 GPUs (new)

-- Clear existing data (for fresh deployments)
DELETE FROM gpu_datacenter_mapping;
DELETE FROM gpu_assets;

-- Insert GPU Assets for DC-EAST-01
INSERT INTO gpu_assets (
    gpu_uuid, model, architecture, compute_capability, memory_gb,
    hostname, datacenter, rack_id, purchase_date, deployment_date,
    sla_tier, priority, tags
) VALUES
    -- DC-EAST-01 GPUs
    (
        'GPU-abc123def456',
        'NVIDIA A100-SXM4-80GB',
        'Ampere',
        '8.0',
        80,
        'gpu-node-east-01',
        'DC-EAST-01',
        'rack-A1',
        CURRENT_DATE - INTERVAL '6 months',
        CURRENT_DATE - INTERVAL '6 months',
        'production',
        3,
        '{"profile": "healthy", "age_months": 6}'::jsonb
    ),
    (
        'GPU-def456abc789',
        'NVIDIA A100-SXM4-80GB',
        'Ampere',
        '8.0',
        80,
        'gpu-node-east-01',
        'DC-EAST-01',
        'rack-A1',
        CURRENT_DATE - INTERVAL '18 months',
        CURRENT_DATE - INTERVAL '18 months',
        'production',
        3,
        '{"profile": "high_temp", "age_months": 18}'::jsonb
    ),
    (
        'GPU-ghi789jkl012',
        'NVIDIA H100-SXM5-80GB',
        'Hopper',
        '9.0',
        80,
        'gpu-node-east-02',
        'DC-EAST-01',
        'rack-A2',
        CURRENT_DATE - INTERVAL '3 months',
        CURRENT_DATE - INTERVAL '3 months',
        'production',
        2,
        '{"profile": "power_hungry", "age_months": 3}'::jsonb
    ),
    (
        'GPU-mno345pqr678',
        'NVIDIA A100-SXM4-80GB',
        'Ampere',
        '8.0',
        80,
        'gpu-node-east-02',
        'DC-EAST-01',
        'rack-A2',
        CURRENT_DATE - INTERVAL '36 months',
        CURRENT_DATE - INTERVAL '36 months',
        'development',
        5,
        '{"profile": "aging", "age_months": 36}'::jsonb
    ),
    (
        'GPU-stu901vwx234',
        'NVIDIA H100-SXM5-80GB',
        'Hopper',
        '9.0',
        80,
        'gpu-node-east-03',
        'DC-EAST-01',
        'rack-A3',
        CURRENT_DATE - INTERVAL '1 month',
        CURRENT_DATE - INTERVAL '1 month',
        'production',
        1,
        '{"profile": "excellent", "age_months": 1}'::jsonb
    ),
    
    -- UK-SOUTH-01 GPUs (New datacenter)
    (
        'GPU-uk1aaa111bbb',
        'NVIDIA H100-SXM5-80GB',
        'Hopper',
        '9.0',
        80,
        'gpu-node-uk-01',
        'UK-SOUTH-01',
        'rack-B1',
        CURRENT_DATE - INTERVAL '8 months',
        CURRENT_DATE - INTERVAL '8 months',
        'production',
        3,
        '{"profile": "unstable_temp", "age_months": 8, "temp_variance": 8.0}'::jsonb
    ),
    (
        'GPU-uk2bbb222ccc',
        'NVIDIA A100-SXM4-80GB',
        'Ampere',
        '8.0',
        80,
        'gpu-node-uk-01',
        'UK-SOUTH-01',
        'rack-B1',
        CURRENT_DATE - INTERVAL '4 months',
        CURRENT_DATE - INTERVAL '4 months',
        'production',
        2,
        '{"profile": "power_efficient", "age_months": 4}'::jsonb
    ),
    (
        'GPU-uk3ccc333ddd',
        'NVIDIA H100-SXM5-80GB',
        'Hopper',
        '9.0',
        80,
        'gpu-node-uk-02',
        'UK-SOUTH-01',
        'rack-B2',
        CURRENT_DATE - INTERVAL '14 months',
        CURRENT_DATE - INTERVAL '14 months',
        'production',
        4,
        '{"profile": "memory_stress", "age_months": 14}'::jsonb
    ),
    (
        'GPU-uk4ddd444eee',
        'NVIDIA A100-SXM4-80GB',
        'Ampere',
        '8.0',
        80,
        'gpu-node-uk-02',
        'UK-SOUTH-01',
        'rack-B2',
        CURRENT_DATE - INTERVAL '22 months',
        CURRENT_DATE - INTERVAL '22 months',
        'production',
        4,
        '{"profile": "intermittent_load", "age_months": 22, "load_pattern": "burst"}'::jsonb
    ),
    (
        'GPU-uk5eee555fff',
        'NVIDIA H100-SXM5-80GB',
        'Hopper',
        '9.0',
        80,
        'gpu-node-uk-03',
        'UK-SOUTH-01',
        'rack-B3',
        CURRENT_DATE - INTERVAL '28 months',
        CURRENT_DATE - INTERVAL '28 months',
        'production',
        5,
        '{"profile": "early_warning", "age_months": 28}'::jsonb
    )
ON CONFLICT (gpu_uuid) DO UPDATE SET
    model = EXCLUDED.model,
    datacenter = EXCLUDED.datacenter,
    rack_id = EXCLUDED.rack_id,
    tags = EXCLUDED.tags,
    updated_at = NOW();

-- Insert Datacenter Mappings
INSERT INTO gpu_datacenter_mapping (gpu_uuid, datacenter, rack_id, location) VALUES
    -- DC-EAST-01
    ('GPU-abc123def456', 'DC-EAST-01', 'rack-A1', 'us-east-1'),
    ('GPU-def456abc789', 'DC-EAST-01', 'rack-A1', 'us-east-1'),
    ('GPU-ghi789jkl012', 'DC-EAST-01', 'rack-A2', 'us-east-1'),
    ('GPU-mno345pqr678', 'DC-EAST-01', 'rack-A2', 'us-east-1'),
    ('GPU-stu901vwx234', 'DC-EAST-01', 'rack-A3', 'us-east-1'),
    
    -- UK-SOUTH-01
    ('GPU-uk1aaa111bbb', 'UK-SOUTH-01', 'rack-B1', 'eu-west-2'),
    ('GPU-uk2bbb222ccc', 'UK-SOUTH-01', 'rack-B1', 'eu-west-2'),
    ('GPU-uk3ccc333ddd', 'UK-SOUTH-01', 'rack-B2', 'eu-west-2'),
    ('GPU-uk4ddd444eee', 'UK-SOUTH-01', 'rack-B2', 'eu-west-2'),
    ('GPU-uk5eee555fff', 'UK-SOUTH-01', 'rack-B3', 'eu-west-2')
ON CONFLICT (gpu_uuid) DO UPDATE SET
    datacenter = EXCLUDED.datacenter,
    rack_id = EXCLUDED.rack_id,
    location = EXCLUDED.location;

-- Verify the data
SELECT 
    datacenter, 
    COUNT(*) as gpu_count,
    STRING_AGG(DISTINCT rack_id, ', ' ORDER BY rack_id) as racks
FROM gpu_datacenter_mapping 
GROUP BY datacenter 
ORDER BY datacenter;

SELECT 
    gpu_uuid, 
    model, 
    datacenter, 
    rack_id,
    tags->>'profile' as profile
FROM gpu_assets 
ORDER BY datacenter, rack_id, gpu_uuid;
