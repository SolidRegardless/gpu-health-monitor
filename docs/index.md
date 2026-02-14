# Documentation Index

**GPU Health Monitor - Complete Documentation Reference**

## 🚀 Getting Started

Start here if you're new to the project:

1. **[Main README](../README.md)** - Project overview and quick start
2. **[Fresh Deployment Guide](../fresh-deployment.md)** - Deploy on a clean system in 60 seconds
3. **[Quick Start Guide](quick-start.md)** - Detailed first-run instructions

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
- **[Technology Deep Dive](TECHNOLOGY_DEEP_DIVE.md)** (50 KB) ⭐ **NEW**
  - Beginner's guide to every technology in the stack
  - Docker, Kafka, TimescaleDB, Grafana, XGBoost, etc.
  - Specific examples for A100/H100 GPU monitoring
  - Production scaling guidance (10,000 GPU fleets)

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

## 🛠️ Deployment & Operations

- **[Deployment Scripts Comparison](../deployment-scripts.md)**
  - Azure CLI vs Terraform deployment methods
  - Prerequisites and feature comparison
  - Troubleshooting deployment issues

- **[Terraform Deployment](../terraform-deployment.md)**
  - Infrastructure-as-code deployment guide
  - Azure resource configuration
  - Network and security setup

- **[Grafana Provisioning](../grafana-provisioning.md)**
  - Automatic dashboard and datasource provisioning
  - Dashboard update procedures
  - Troubleshooting panel issues

- **[Interview Demo Guide](../interview-demo-guide.md)**
  - Complete walkthrough for demonstrations
  - Key features and talking points
  - Common questions and answers

- **[Predictive Analytics Guide](../predictive-analytics.md)**
  - ML-based failure prediction features
  - Dashboard panel descriptions
  - Data requirements and interpretation

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
| Technology Deep Dive | 50 KB | 2026-02-13 | ⭐ **NEW** |
| System Architecture | 59 KB | 2026-02-11 | ✅ Current |
| POC Implementation | 43 KB | 2026-02-11 | ✅ Current |
| Fresh Deployment | 7 KB | 2026-02-13 | ✅ Current |
| Deployment Scripts | 6 KB | 2026-02-13 | ✅ Current |
| Terraform Deployment | 8 KB | 2026-02-11 | ✅ Current |
| Grafana Provisioning | 8 KB | 2026-02-13 | ✅ Current |
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

**Total Documentation:** 10 core files + 9 in docs/ (~170 KB)  
**Format:** Markdown with Mermaid diagrams  
**Version Control:** All docs in Git  
**Note:** Transient fix documentation consolidated into CHANGELOG.md
