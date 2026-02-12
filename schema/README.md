# GPU Health Monitor - Database Schema

This directory contains SQL schema files for initializing the TimescaleDB database.

## Files

| File | Purpose | Run Order |
|------|---------|-----------|
| `01_init_schema.sql` | Core tables, hypertables, indexes, views | **1st** |
| `02_aggregates.sql` | Continuous aggregates (1min, 5min, 1hour) | **2nd** |
| `03_anomalies.sql` | Anomaly detection table | **3rd** |

## Setup Order

**IMPORTANT:** These files must be run in numeric order (01, 02, 03).

### Fresh Database Setup

```bash
# From the docker directory
cd docker

# Apply all schema files in order
docker compose exec timescaledb psql -U gpu_monitor -d gpu_health < ../schema/01_init_schema.sql
docker compose exec timescaledb psql -U gpu_monitor -d gpu_health < ../schema/02_aggregates.sql
docker compose exec timescaledb psql -U gpu_monitor -d gpu_health < ../schema/03_anomalies.sql
```

### Re-applying Aggregates

If continuous aggregates were created incorrectly (as regular tables), the `02_aggregates.sql` script will:

1. Drop any incorrectly created tables (`DROP TABLE IF EXISTS ...`)
2. Recreate them as proper continuous aggregates (`WITH (timescaledb.continuous)`)
3. Set up automatic refresh policies
4. Create indexes
5. Grant permissions

The script is idempotent and safe to re-run.

## Key Points

### Continuous Aggregates vs Regular Tables

**Continuous Aggregates** (correct):
- Created with `CREATE MATERIALIZED VIEW ... WITH (timescaledb.continuous)`
- Automatically updated by TimescaleDB
- Optimized for fast time-series queries
- Support automatic refresh policies

**Regular Hypertables** (incorrect):
- Created with `CREATE TABLE ...`
- Must be manually populated
- Less efficient for aggregated queries

### Verification

Check that aggregates were created correctly:

```sql
-- Should show all three continuous aggregates
SELECT view_name, materialized_only 
FROM timescaledb_information.continuous_aggregates 
ORDER BY view_name;

-- Should return:
-- gpu_metrics_1hour | t
-- gpu_metrics_1min  | t
-- gpu_metrics_5min  | t
```

## Troubleshooting

### Issue: No data in continuous aggregates

**Cause:** They were created as regular tables instead of continuous aggregates.

**Fix:**
```bash
docker compose exec timescaledb psql -U gpu_monitor -d gpu_health < ../schema/02_aggregates.sql
```

The script will automatically drop the incorrectly created tables and recreate them properly.

### Issue: "table already exists" error

**Cause:** Previous failed run created a regular table.

**Fix:**
```sql
-- Manually drop the table
DROP TABLE IF EXISTS gpu_metrics_1min CASCADE;
DROP TABLE IF EXISTS gpu_metrics_5min CASCADE;
DROP TABLE IF EXISTS gpu_metrics_1hour CASCADE;

-- Then re-run the aggregates script
\i 02_aggregates.sql
```

## Schema Evolution

When adding new schema changes:

1. Create a new numbered file (e.g., `04_new_feature.sql`)
2. Update this README with the new file
3. Make the script idempotent (use `IF NOT EXISTS`, `DROP ... IF EXISTS`, etc.)
4. Document the purpose and any dependencies

## Maintenance Scripts

### View all continuous aggregate policies

```sql
SELECT view_name, schedule_interval, config
FROM timescaledb_information.jobs
WHERE application_name LIKE '%Continuous Aggregate%';
```

### Manually refresh an aggregate

```sql
CALL refresh_continuous_aggregate('gpu_metrics_1min', NULL, NULL);
```

### Check data counts

```sql
SELECT 'Raw metrics' as source, COUNT(*) FROM gpu_metrics
UNION ALL
SELECT '1-minute agg', COUNT(*) FROM gpu_metrics_1min
UNION ALL
SELECT '5-minute agg', COUNT(*) FROM gpu_metrics_5min
UNION ALL
SELECT '1-hour agg', COUNT(*) FROM gpu_metrics_1hour;
```
