# Documentation Index

**GPU Health Monitor - Complete Documentation Reference**

## 🚀 Getting Started

Start here if you're new to the project:

1. **[Main README](../README.md)** - Project overview and quick start
2. **[Fresh Deployment Guide](../fresh-deployment.md)** - Deploy on a clean system in 60 seconds
3. **[Quick Start Guide](quick-start.md)** - Detailed first-run instructions
4. **[Current Status](../current-status.md)** - Latest implementation status

## 📚 Core Documentation

### System Design
- **[System Architecture](../gpu-health-system-architecture.md)** (59 KB)
  - Complete technical architecture
  - Data models and health definitions
  - Economic decision engine
  - Security and compliance

- **[POC Implementation Guide](../gpu-health-poc-implementation.md)** (43 KB)
  - 6-week proof-of-concept plan
  - Step-by-step deployment for 50 GPUs
  - Budget and resource planning

### Technical Reference
- **[Database Tables Explained](database-tables-explained.md)** (8 KB)
  - Complete schema documentation
  - Table relationships
  - Index and compression strategies

- **[ML Tech Stack](ml-tech-stack.md)** (7 KB)
  - Machine learning models (XGBoost, LSTM)
  - Python dependencies
  - Model training pipeline

- **[Schema README](../schema/README.md)**
  - SQL initialization scripts
  - Migration guide
  - Data seeding

## 🏗️ Architecture Deep-Dives

Located in `docs/architecture/`:

- **[DCGM Integration](architecture/dcgm-integration.md)** - NVIDIA Data Center GPU Manager setup
- **[Kafka Integration](architecture/kafka-integration.md)** - Event streaming architecture
- **[TimescaleDB Integration](architecture/timescaledb-integration.md)** - Time-series database design
- **[ML Pipeline Architecture](architecture/ml-pipeline-architecture.md)** - Machine learning workflow

## 🛠️ Development

- **[Development Setup](development/setup.md)** - Local dev environment configuration
- **[Docs Overview](README.md)** - Documentation structure

## 📊 Grafana Dashboards

The system includes 6 pre-configured dashboards:

1. **GPU Fleet Overview** - Aggregate stats for all GPUs
2. **GPU Detail Dashboard** - Deep-dive into individual GPUs
3. **Datacenter Overview** - Rack-level aggregation and filtering
4. **GPU Health Monitor Overview** - Health scoring visualization
5. **GPU Health Monitor - Simple** - Simplified quick view
6. **GPU Predictive Analytics** - ML-based failure forecasting ⚠️ See fixes below

Access: http://localhost:3000 (admin/admin)

## 🔧 Troubleshooting & Fixes

### Production Fixes (2026-02-13)

- **[Predictive Dashboard Fix](../PREDICTIVE_DASHBOARD_FIX.md)** (8 KB)
  - Complete fix for "No Data" issues in predictive analytics dashboard
  - Feature engineering column name corrections
  - Dashboard variable configuration
  - Styled failure type panel with emojis
  
- **[Gauge Visualization Fix](../GAUGE_FIX_SUMMARY.md)** (9 KB)
  - Fixed 13 gauge panels across 4 dashboards
  - All gauges now show filled progress bars
  - Min/max configuration guide

- **[Schema Initialization Fix](../DEPLOYMENT_FIX.md)** (4 KB)
  - Resolved database initialization conflicts
  - Correct schema file ordering
  - Column name corrections

## 🔧 Quick Reference

### One-Command Deployment
```bash
docker-compose -f docker/docker-compose.yml up -d
```

### Key Ports
- **3000** - Grafana
- **5432** - TimescaleDB
- **9092-9093** - Kafka
- **8000** - REST API
- **9400** - Mock DCGM

### Database Access
```bash
docker exec -it gpu-monitor-timescaledb psql -U gpu_monitor -d gpu_health
```

### Service Logs
```bash
docker logs gpu-monitor-<service-name> --tail 50 --follow
```

## 📈 Documentation Status

| Document | Size | Last Updated | Status |
|----------|------|--------------|--------|
| System Architecture | 59 KB | 2026-02-11 | ✅ Current |
| POC Implementation | 43 KB | 2026-02-11 | ✅ Current |
| Current Status | 12 KB | 2026-02-13 | ✅ Current |
| Fresh Deployment | 7 KB | 2026-02-13 | ✅ Current |
| Database Tables | 8 KB | 2026-02-12 | ✅ Current |
| ML Tech Stack | 7 KB | 2026-02-12 | ✅ Current |
| Quick Start | 9 KB | 2026-02-11 | ✅ Current |

## 🤝 Contributing

When adding documentation:

1. Update this index
2. Follow Markdown best practices
3. Include diagrams where helpful (mermaid supported)
4. Keep docs DRY (Don't Repeat Yourself)
5. Update the "Last Updated" date

## 📞 Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Documentation Fixes**: Submit PR to relevant `.md` file

---

**Total Documentation:** 15 files (~160 KB)  
**Format:** Markdown with Mermaid diagrams  
**Version Control:** All docs in Git  
