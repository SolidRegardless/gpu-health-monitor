# Grafana Dashboard Fixed

**Issue:** Dashboard showing no data  
**Fixed:** 2026-02-12 10:18 GMT

## 🔧 Problem Identified

The dashboard JSON was referencing the datasource by **name** instead of by **UID**:

```json
{
  "datasource": {
    "type": "postgres",
    "uid": "GPU Health TimescaleDB"  // ❌ This is a name, not a UID!
  }
}
```

Grafana datasources are identified by auto-generated UIDs, not names. The actual UID is: `P0D1C26D7DC78F49D`

## ✅ Solution Applied

Updated all panel datasource references in the dashboard:

```json
{
  "datasource": {
    "type": "postgres",
    "uid": "P0D1C26D7DC78F49D"  // ✅ Correct UID!
  }
}
```

**Files updated:**
- `config/grafana/dashboards/gpu-overview.json` (fixed all panels)
- Backup created: `gpu-overview.json.backup`

**Services restarted:**
- Grafana container restarted to pick up new dashboard

## 📊 Dashboard Details

**Dashboard:** GPU Health Monitor Overview  
**UID:** `gpu-health-overview`  
**URL:** http://localhost:3000/d/gpu-health-overview/gpu-health-monitor-overview

**Datasource:** GPU Health TimescaleDB  
**UID:** `P0D1C26D7DC78F49D`  
**Type:** PostgreSQL (with TimescaleDB support)  
**Connection:** ✅ Working (tested successfully)

## 🎯 Current Data Available

- **895 metrics** in database (as of 10:18 GMT)
- Latest metric: 2026-02-12 10:18:12
- All tables populated with fresh data
- API queries working correctly

## 🖥️ Dashboard Panels

The dashboard includes:

1. **Overall Health Score** (gauge) - Latest health score
2. **GPU Temperature** (time series) - Real-time temp data
3. **Power Usage** (time series) - Power consumption
4. **GPU Utilization** (time series) - Compute usage
5. **Memory Usage** (time series) - VRAM utilization
6. **ECC Errors** (stat) - Error counts

All panels should now display data correctly!

## ✅ Verification

Test the datasource connection:
```bash
curl -u admin:admin http://localhost:3000/api/datasources/uid/P0D1C26D7DC78F49D
```

Test a query:
```bash
curl -u admin:admin -X POST http://localhost:3000/api/ds/query \
  -H "Content-Type: application/json" \
  -d '{
    "queries": [{
      "datasource": {"uid": "P0D1C26D7DC78F49D"},
      "rawSql": "SELECT COUNT(*) FROM gpu_metrics",
      "format": "table",
      "refId": "A"
    }]
  }'
```

## 🎨 Access Dashboard

**URL:** http://localhost:3000/d/gpu-health-overview/gpu-health-monitor-overview  
**Login:** admin / admin  
**Refresh:** Auto-refresh set to 5 seconds

The dashboard should now show live GPU metrics! 📊
