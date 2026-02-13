# Grafana Provisioning Guide

**Status**: ✅ Fully Automated  
**Last Updated**: 2026-02-13

## Overview

Grafana dashboards and datasources are automatically provisioned on container startup via volume mounts. No manual configuration required.

## Directory Structure

```
config/grafana/
├── dashboards/
│   ├── dashboards.yaml           ← Provisioning config
│   ├── datacenter-overview.json  ← Dashboard: Datacenter view
│   ├── gpu-detail.json           ← Dashboard: Individual GPU detail
│   ├── gpu-fleet-overview.json   ← Dashboard: Fleet-wide metrics
│   ├── gpu-overview.json         ← Dashboard: GPU health overview
│   ├── gpu-overview-simple.json  ← Dashboard: Simplified view
│   └── gpu-predictive.json       ← Dashboard: ML predictions ✨
└── datasources/
    └── timescaledb.yaml          ← TimescaleDB datasource
```

## How It Works

### Docker Compose Volume Mount
```yaml
grafana:
  image: grafana/grafana:latest
  volumes:
    - ../config/grafana:/etc/grafana/provisioning
```

The entire `config/grafana/` directory is mounted to Grafana's provisioning path, enabling automatic:
- **Datasource configuration** (TimescaleDB connection)
- **Dashboard deployment** (all 6 dashboards)
- **Live updates** (changes detected every 10 seconds)

## Provisioning Configuration

### dashboards.yaml
```yaml
apiVersion: 1
providers:
  - name: 'GPU Health Monitor'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10  # Check for changes every 10s
    allowUiUpdates: true        # Allow edits in Grafana UI
    options:
      path: /etc/grafana/provisioning/dashboards
```

### timescaledb.yaml
```yaml
apiVersion: 1
datasources:
  - name: GPU Health TimescaleDB
    type: postgres
    access: proxy
    url: timescaledb:5432
    database: gpu_health
    user: gpu_monitor
    secureJsonData:
      password: gpu_monitor_secret
    jsonData:
      sslmode: 'disable'
      postgresVersion: 1500
      timescaledb: true
    editable: true
    isDefault: true
```

## Dashboard List

| Dashboard | File | Status | Notes |
|-----------|------|--------|-------|
| **GPU Fleet Overview** | gpu-fleet-overview.json | ✅ Fixed | All 6 gauges display correctly |
| **GPU Detail** | gpu-detail.json | ✅ Fixed | GPU utilization gauge fixed |
| **Datacenter Overview** | datacenter-overview.json | ✅ Fixed | 3 gauges with time filters |
| **GPU Overview** | gpu-overview.json | ✅ Fixed | Health score gauge fixed |
| **GPU Overview (Simple)** | gpu-overview-simple.json | ✅ Working | Simplified metrics view |
| **GPU Predictive Analytics** | gpu-predictive.json | ✅ Fixed | Failure type uses table panel |

## Recent Fixes Applied

### Predictive Dashboard (gpu-predictive.json)
**Date**: 2026-02-13

**Issues Fixed**:
1. ✅ No default GPU variable selection → Added default GPU
2. ✅ Predicted Failure Type showing "No Data" → Changed to table panel
3. ✅ Feature engineering column mismatches → Fixed in service code

**Current State**:
- Default GPU: Auto-selects first GPU alphabetically
- Failure Type Panel: Table panel with orange background
- All panels operational with 5+ prediction cycles

### Gauge Panels (All Dashboards)
**Date**: 2026-02-13

**Issues Fixed**:
- ✅ 13 gauge panels missing filled progress bars
- ✅ Added min/max configuration to all gauges
- ✅ Added time filters to datacenter aggregates

**Details**: See `GAUGE_FIX_SUMMARY.md`

## Updating Dashboards

### Method 1: Edit Local File + Restart (Recommended)
```bash
# 1. Edit the dashboard JSON locally
vim config/grafana/dashboards/gpu-predictive.json

# 2. Copy to deployed location
scp config/grafana/dashboards/gpu-predictive.json user@host:/path/

# 3. Restart Grafana (picks up changes)
docker restart gpu-monitor-grafana
```

### Method 2: Edit in Grafana UI
1. Open dashboard in Grafana
2. Make changes
3. Click "Save dashboard"
4. Export JSON: Settings → JSON Model → Copy
5. Save to `config/grafana/dashboards/<name>.json`
6. Commit to git

**Note**: UI changes persist in Grafana's database but won't survive container recreation unless exported to JSON.

### Method 3: Fresh Deployment
```bash
# Dashboards automatically provisioned on first start
docker-compose -f docker/docker-compose.yml up -d
```

## Troubleshooting

### Dashboard Not Appearing
**Symptoms**: Dashboard missing in Grafana UI after container start

**Checks**:
```bash
# 1. Verify file exists
ls config/grafana/dashboards/gpu-predictive.json

# 2. Check JSON syntax
cat config/grafana/dashboards/gpu-predictive.json | jq . > /dev/null

# 3. Check Grafana logs
docker logs gpu-monitor-grafana | grep -i provision

# 4. Verify volume mount
docker inspect gpu-monitor-grafana | grep -A 5 Mounts
```

**Solutions**:
- Invalid JSON → Fix syntax errors
- Wrong path → Check volume mount in docker-compose.yml
- Permission issues → `chmod 644 config/grafana/dashboards/*.json`

### Panel Shows "No Data"
**Symptoms**: Panel displays "No Data" despite data in database

**Common Causes**:
1. **Variable not selected**: Check GPU dropdown at top
2. **Time range**: Ensure time range includes data timestamps
3. **Query error**: Open Query Inspector (panel menu → Inspect → Query)
4. **Datasource down**: Check TimescaleDB connectivity

**Debug**:
```bash
# Test query directly
docker exec gpu-monitor-timescaledb psql -U gpu_monitor -d gpu_health -c \
  "SELECT predicted_failure_type FROM gpu_failure_predictions LIMIT 5;"

# Check Grafana datasource
curl -u admin:admin http://localhost:3000/api/datasources
```

### Stat Panel Not Displaying Text
**Symptoms**: Stat panel shows "No Data" for text fields like "thermal", "power"

**Root Cause**: Grafana stat panels don't reliably render text values

**Solution**: Use table panel with stat-like styling:
```json
{
  "type": "table",
  "options": {
    "showHeader": false
  },
  "fieldConfig": {
    "defaults": {
      "custom": {
        "displayMode": "color-background",
        "align": "center"
      }
    }
  }
}
```

## Accessing Grafana

- **URL**: http://localhost:3000 (or http://<VM-IP>:3000)
- **Username**: admin
- **Password**: admin (default) or admin123 (if changed)

## Security Notes

### Production Recommendations
1. **Change admin password**: Environment variable `GF_SECURITY_ADMIN_PASSWORD`
2. **Enable TLS**: Configure reverse proxy (nginx/traefik)
3. **Restrict access**: Firewall rules or VPN
4. **Use secrets**: Store credentials in Docker secrets or vault

### Current Configuration (Development)
- ⚠️ Default credentials (admin/admin)
- ⚠️ No TLS (HTTP only)
- ⚠️ Public port 3000 exposed

**For production deployment**: Update docker-compose.yml with secure configuration.

## Related Documentation

- **[GAUGE_FIX_SUMMARY.md](GAUGE_FIX_SUMMARY.md)** - Gauge panel fix details
- **[PREDICTIVE_DASHBOARD_FIX.md](PREDICTIVE_DASHBOARD_FIX.md)** - Predictive analytics fixes
- **[DEPLOYMENT_SCRIPTS.md](DEPLOYMENT_SCRIPTS.md)** - Deployment methods
- **[FRESH_DEPLOYMENT.md](FRESH_DEPLOYMENT.md)** - Fresh deployment guide

## Verification Checklist

After deployment, verify:

- [ ] Grafana accessible at port 3000
- [ ] TimescaleDB datasource shows green (healthy)
- [ ] All 6 dashboards visible in sidebar
- [ ] GPU selector dropdown populates with GPU UUIDs
- [ ] Gauges show filled progress bars (not just numbers)
- [ ] Predictive dashboard displays failure types
- [ ] Time-series charts render data points

## Commands Reference

```bash
# Restart Grafana
docker restart gpu-monitor-grafana

# Check logs
docker logs -f gpu-monitor-grafana

# Test datasource connectivity
docker exec gpu-monitor-grafana curl -s http://timescaledb:5432 || echo "DB unreachable"

# List provisioned dashboards
docker exec gpu-monitor-grafana ls -la /etc/grafana/provisioning/dashboards/

# Validate JSON syntax
find config/grafana/dashboards/ -name "*.json" -exec echo "Checking {}" \; -exec jq . {} > /dev/null \;

# Export dashboard from Grafana
curl -u admin:admin http://localhost:3000/api/dashboards/uid/gpu-predictive | jq .dashboard > backup.json
```

---

**Status**: ✅ All dashboards provisioned and operational  
**Last Verified**: 2026-02-13 14:56 GMT
