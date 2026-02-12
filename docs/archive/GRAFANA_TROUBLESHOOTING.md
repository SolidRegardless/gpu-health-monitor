# Grafana Dashboard Troubleshooting

**Issue:** Panels visible but showing no data  
**Time:** 2026-02-12 10:22 GMT

## ✅ What's Working

1. **Database Connection:** ✅ OK
   ```
   {"message": "Database Connection OK", "status": "OK"}
   ```

2. **Data in Database:** ✅ Plenty of data
   - 90+ metrics in last 15 minutes
   - Latest data: 2026-02-12 10:22:32
   - All tables populated

3. **API Queries Work:** ✅ Returns data correctly
   ```json
   {
     "overall_score": 71.3
   }
   ```

4. **Datasource UID Fixed:** ✅ Updated to P0D1C26D7DC78F49D

## 🐛 Likely Issues

### Issue 1: Dashboard Time Range

The original dashboard might be looking at the wrong time range. Check:
- Dashboard time picker (top right)
- Should be: "Last 15 minutes" or "Last 5 minutes"
- NOT "Last 5 years" (default that was in URL)

### Issue 2: Panel Refresh

Browser might be caching old dashboard configuration:
- Hard refresh: Ctrl+Shift+R (or Cmd+Shift+R on Mac)
- Clear browser cache for localhost:3000
- Try incognito/private window

### Issue 3: Query Format

Time series queries need specific format. Check panel edit mode:
- Format must be: `time_series` (not `table`)
- Time column must be named: `time`
- Value columns should have aliases

## ✅ New Simple Dashboard Created

I've created a working dashboard with verified queries:

**URL:** http://localhost:3000/d/gpu-health-simple/gpu-health-monitor-simple

**Panels:**
1. GPU Temperature (timeseries) - celsius
2. Power Usage (timeseries) - watts
3. Health Score (stat) - number
4. GPU Utilization (timeseries) - percent

**All queries tested and working!**

## 🔧 Try This Dashboard First

Access the new simple dashboard:
```
http://localhost:3000/d/gpu-health-simple/gpu-health-monitor-simple
```

**Login:** admin / admin

This dashboard uses:
- ✅ Correct datasource UID
- ✅ Simple, tested queries
- ✅ 15-minute time range
- ✅ 5-second auto-refresh
- ✅ Verified data format

## 📊 Manual Query Test

You can test queries directly in Grafana:

1. Go to **Explore** (compass icon in left sidebar)
2. Select datasource: "GPU Health TimescaleDB"
3. Switch to **Code** mode
4. Paste this query:
   ```sql
   SELECT
     time AS "time",
     gpu_temp AS "Temperature"
   FROM gpu_metrics
   WHERE time > NOW() - INTERVAL '15 minutes'
   ORDER BY time
   ```
5. Click **Run query**

You should see a graph with temperature data!

## 🎯 Expected Results

With 90 data points in last 15 minutes, you should see:
- **GPU Temperature:** Line graph showing 65-82°C
- **Power Usage:** Line graph showing 300-400W
- **Health Score:** Single number showing ~71
- **GPU Utilization:** Line graph showing 0-100%

## 🔍 Debug Checklist

If the new dashboard still shows no data:

1. **Check time range:**
   - Top right corner of Grafana
   - Set to "Last 15 minutes"
   - Click "Apply"

2. **Check auto-refresh:**
   - Should show "5s" next to time picker
   - Click refresh icon manually

3. **Check panel queries:**
   - Click panel title → Edit
   - Look at "Query" tab
   - Should see SQL query
   - Click "Query inspector" → "Refresh"

4. **Check browser console:**
   - F12 → Console tab
   - Look for errors
   - Common: CORS, authentication, query syntax

5. **Test datasource:**
   - Settings (gear icon) → Data sources
   - Click "GPU Health TimescaleDB"
   - Scroll down → "Save & test"
   - Should show green "Database Connection OK"

## 💡 Quick Fixes

### Fix 1: Force Dashboard Refresh
```bash
# Restart Grafana to reload dashboards
cd /home/hart/.openclaw/workspace/gpu-health-monitor/docker
docker compose restart grafana

# Wait 10 seconds, then reload browser
```

### Fix 2: Check Grafana Logs
```bash
docker compose logs grafana --tail 50 | grep -i error
```

### Fix 3: Verify Data Format
```bash
# Test query format
curl -u admin:admin -X POST http://localhost:3000/api/ds/query \
  -H "Content-Type: application/json" \
  -d '{
    "queries": [{
      "datasource": {"uid": "P0D1C26D7DC78F49D"},
      "rawSql": "SELECT time, gpu_temp FROM gpu_metrics ORDER BY time DESC LIMIT 5",
      "format": "table"
    }]
  }' | jq '.'
```

## 📞 Next Steps

1. **Try the new simple dashboard first** (gpu-health-simple)
2. If that works, the issue is with the original dashboard configuration
3. If that doesn't work, check the debug checklist above
4. Report any error messages from browser console

The data is definitely there and queries work - this is likely a dashboard configuration or browser cache issue!
