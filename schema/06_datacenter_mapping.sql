-- Datacenter and GPU Mapping
-- Maps GPUs to datacenters, racks, and clusters for organizational views

CREATE TABLE IF NOT EXISTS gpu_datacenter_mapping (
    gpu_uuid TEXT PRIMARY KEY,
    datacenter TEXT NOT NULL,
    rack_id TEXT,
    cluster_name TEXT,
    location TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_datacenter_mapping_dc ON gpu_datacenter_mapping (datacenter);
CREATE INDEX IF NOT EXISTS idx_datacenter_mapping_rack ON gpu_datacenter_mapping (rack_id);
CREATE INDEX IF NOT EXISTS idx_datacenter_mapping_cluster ON gpu_datacenter_mapping (cluster_name);

-- Trigger for auto-updating updated_at
CREATE TRIGGER update_datacenter_mapping_updated_at
    BEFORE UPDATE ON gpu_datacenter_mapping
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Seed data: Map all 5 GPUs to datacenter
INSERT INTO gpu_datacenter_mapping (gpu_uuid, datacenter, rack_id, cluster_name, location) VALUES
('GPU-abc123def456', 'DC-EAST-01', 'rack-A1', 'gpu-cluster-prod', 'US-East'),
('GPU-def456abc789', 'DC-EAST-01', 'rack-A1', 'gpu-cluster-prod', 'US-East'),
('GPU-ghi789jkl012', 'DC-EAST-01', 'rack-A2', 'gpu-cluster-prod', 'US-East'),
('GPU-mno345pqr678', 'DC-EAST-01', 'rack-A2', 'gpu-cluster-prod', 'US-East'),
('GPU-stu901vwx234', 'DC-EAST-01', 'rack-A3', 'gpu-cluster-prod', 'US-East')
ON CONFLICT (gpu_uuid) DO NOTHING;

COMMIT;
