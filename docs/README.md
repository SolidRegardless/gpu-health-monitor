# GPU Health Monitor Documentation

## Overview

This directory contains comprehensive technical documentation for the GPU Health Monitor system, a production-grade monitoring and predictive maintenance platform for NVIDIA A100/H100 GPU fleets.

**📖 See [Documentation Index](index.md) for a complete guide to all documentation.**

## Documentation Structure

### Architecture Documents (`architecture/`)

Detailed technical architecture and integration guides for core system components:

- **[DCGM Integration Guide](architecture/dcgm-integration.md)** - NVIDIA Data Center GPU Manager integration, metrics collection, data models, and telemetry pipeline
- **[Kafka & Stream Processing Architecture](architecture/kafka-integration.md)** - Event streaming, real-time processing, topic design, and stream processing pipelines
- **[TimescaleDB Integration Guide](architecture/timescaledb-integration.md)** - Time-series database design, schema, compression, retention, and query optimization
- **[ML Pipeline Architecture](architecture/ml-pipeline-architecture.md)** - Machine learning pipeline, health scoring, failure prediction, and economic decision engine

Each architecture document includes:
- System context and rationale
- Detailed architecture diagrams (Mermaid)
- Implementation code examples
- Configuration specifications
- Performance considerations
- Operational procedures
- Monitoring and troubleshooting guides

### Main Project Documents

- **[README.md](../README.md)** - Project overview, features, and quick start
- **[System Architecture](../gpu-health-system-architecture.md)** - Complete system architecture and design
- **[POC Implementation Guide](../gpu-health-poc-implementation.md)** - Step-by-step proof-of-concept deployment

## Document Conventions

All architecture documents follow a consistent structure:

1. **Overview** - Purpose, context, and rationale
2. **Architecture** - System design, components, and interactions
3. **Implementation** - Code examples, configurations, and deployment
4. **Operations** - Monitoring, troubleshooting, and maintenance
5. **Performance & Scaling** - Optimization and capacity planning
6. **References** - External resources and further reading

## Document Metadata

Each document includes:
- **Document Version** - Semantic version number
- **Last Updated** - Date of last revision
- **Maintained By** - Primary document owner and contact
- **Project** - Project name and scope

## Contributing

When updating architecture documents:

1. Maintain consistency with existing document structure
2. Include practical code examples where applicable
3. Update mermaid diagrams to reflect changes
4. Increment document version appropriately
5. Update "Last Updated" date
6. Ensure all external references are current

## Document Versions

| Document | Version | Last Updated |
|----------|---------|--------------|
| DCGM Integration | 1.1 | 2026-02-11 |
| Kafka Integration | 1.0 | 2026-02-11 |
| TimescaleDB Integration | 1.0 | 2026-02-11 |
| ML Pipeline Architecture | 1.0 | 2026-02-11 |

## License

See [LICENSE](../LICENSE) in the project root.

## Contact

**Project Maintainer**: Stuart Hart (stuarthart@msn.com)

For questions, issues, or contributions, please open an issue on the project repository.
