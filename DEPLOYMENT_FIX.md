# Deployment Fix - 2026-02-13

## Issue: Schema Initialization Failure

### Problem
During Azure VM deployment, the TimescaleDB container was failing to start due to conflicting schema files:

1. **File conflict**: Both `01_init_schema.sql` and `01_init_schema_multi_gpu.sql` existed
2. **Column mismatch**: The multi-GPU file tried to INSERT with `serial_number` column that doesn't exist in the schema
3. **Wrong execution order**: Data inserts were running before schema was fully created

### Symptoms
- TimescaleDB container exited with code 3
- Error: `column "serial_number" of relation "gpu_assets" does not exist`
- Grafana dashboards showed no data
- Enricher logs showed "No asset metadata found for GPU"

### Root Cause
The `01_init_schema_multi_gpu.sql` file was:
1. Conflicting with the primary schema file (both named `01_*`)
2. Using incorrect column names (`serial_number`, `location` instead of schema-defined columns)
3. Trying to insert data before continuous aggregates were created

### Fix Applied

**1. Removed conflicting file:**
```bash
rm schema/01_init_schema_multi_gpu.sql
```

**2. Created proper data initialization file:**
- New file: `schema/07_init_multi_gpu_data.sql`
- Uses correct column names: `datacenter`, `rack_id`, `location` (not `serial_number`)
- Runs AFTER all schema files (numbered 01-06)
- Includes ON CONFLICT clauses for idempotency

**3. Correct column mapping:**
```sql
-- OLD (broken):
INSERT INTO gpu_assets (..., serial_number, location, ...)

-- NEW (working):
INSERT INTO gpu_assets (..., datacenter, rack_id, ...)
```

### Verification
After fix:
```sql
SELECT COUNT(*) FROM gpu_metrics;
-- Result: 136+ records, all 5 GPUs reporting

SELECT * FROM gpu_assets;
-- Result: 5 rows with correct metadata
```

### Files Changed
- **Deleted**: `schema/01_init_schema_multi_gpu.sql`
- **Created**: `schema/07_init_multi_gpu_data.sql`
- **Preserved**: All other schema files (01-06) unchanged

### Prevention
- Schema files numbered 01-06 define structure
- Data files numbered 07+ populate initial data
- Never use `serial_number` column (doesn't exist in schema)
- Always use `datacenter`, `rack_id`, `location` for placement

### Testing Fresh Deployment
```bash
cd docker
docker-compose down -v  # Clean slate
docker-compose up -d    # Should work without errors
sleep 30
docker logs gpu-monitor-timescaledb | grep ERROR  # Should be empty
docker exec gpu-monitor-timescaledb psql -U gpu_monitor -d gpu_health -c "SELECT COUNT(*) FROM gpu_assets;"  # Should return 5
```

---
**Status**: ✅ Fixed and tested on Azure VM (98.71.11.28)  
**Data Flowing**: ✅ All 5 GPUs reporting metrics to Grafana
