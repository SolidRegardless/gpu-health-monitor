#!/usr/bin/env python3
"""
GPU Health Monitor - GitHub Issues Creator
Creates complete agile project structure with milestones, labels, and issues
"""

import os
import requests
import json
from datetime import datetime, timedelta

# Configuration
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
REPO_OWNER = 'SolidRegardless'
REPO_NAME = 'gpu-health-monitor'
API_BASE = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}'

headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

# Color scheme for labels
COLORS = {
    'epic': 'D73A4A',
    'feature': '0075CA',
    'enhancement': 'A2EEEF',
    'bug': 'D93F0B',
    'documentation': '0E8A16',
    'infrastructure': 'FBCA04',
    'backend': '5319E7',
    'frontend': 'C5DEF5',
    'ml': 'D4C5F9',
    'data-pipeline': 'BFD4F2',
    'database': 'F9D0C4',
    'monitoring': 'FEF2C0',
    'P0-critical': 'B60205',
    'P1-high': 'D93F0B',
    'P2-medium': 'FBCA04',
    'P3-low': 'C5DEF5',
}

def create_labels():
    """Create all project labels"""
    labels = [
        # Type labels
        {'name': 'epic', 'description': 'Large feature spanning multiple issues', 'color': COLORS['epic']},
        {'name': 'feature', 'description': 'New functionality', 'color': COLORS['feature']},
        {'name': 'enhancement', 'description': 'Improvement to existing feature', 'color': COLORS['enhancement']},
        {'name': 'bug', 'description': 'Something broken', 'color': COLORS['bug']},
        {'name': 'documentation', 'description': 'Documentation only', 'color': COLORS['documentation']},
        {'name': 'infrastructure', 'description': 'DevOps/Infrastructure work', 'color': COLORS['infrastructure']},
        
        # Area labels
        {'name': 'backend', 'description': 'Backend services', 'color': COLORS['backend']},
        {'name': 'frontend', 'description': 'UI/UX', 'color': COLORS['frontend']},
        {'name': 'ml', 'description': 'Machine learning', 'color': COLORS['ml']},
        {'name': 'data-pipeline', 'description': 'Data processing', 'color': COLORS['data-pipeline']},
        {'name': 'database', 'description': 'Database schema and queries', 'color': COLORS['database']},
        {'name': 'monitoring', 'description': 'Observability', 'color': COLORS['monitoring']},
        
        # Priority labels
        {'name': 'P0-critical', 'description': 'Blocking issue', 'color': COLORS['P0-critical']},
        {'name': 'P1-high', 'description': 'Important', 'color': COLORS['P1-high']},
        {'name': 'P2-medium', 'description': 'Normal priority', 'color': COLORS['P2-medium']},
        {'name': 'P3-low', 'description': 'Nice to have', 'color': COLORS['P3-low']},
    ]
    
    print("Creating labels...")
    for label in labels:
        try:
            response = requests.post(
                f'{API_BASE}/labels',
                headers=headers,
                json=label
            )
            if response.status_code == 201:
                print(f"✓ Created label: {label['name']}")
            elif response.status_code == 422:
                print(f"- Label already exists: {label['name']}")
            else:
                print(f"✗ Failed to create label {label['name']}: {response.status_code}")
        except Exception as e:
            print(f"✗ Error creating label {label['name']}: {e}")

def create_milestones():
    """Create project milestones (phases)"""
    start_date = datetime.now()
    
    milestones = [
        {
            'title': 'Phase 1: Foundation',
            'description': 'Establish core telemetry pipeline and basic monitoring (Weeks 1-4)',
            'due_on': (start_date + timedelta(weeks=4)).isoformat(),
        },
        {
            'title': 'Phase 2: Health Scoring',
            'description': 'Implement multi-dimensional health scoring system (Weeks 5-8)',
            'due_on': (start_date + timedelta(weeks=8)).isoformat(),
        },
        {
            'title': 'Phase 3: Predictive Analytics',
            'description': 'Build failure prediction models with historical data (Weeks 9-14)',
            'due_on': (start_date + timedelta(weeks=14)).isoformat(),
        },
        {
            'title': 'Phase 4: Economic Engine',
            'description': 'Implement economic decision-making framework (Weeks 15-18)',
            'due_on': (start_date + timedelta(weeks=18)).isoformat(),
        },
        {
            'title': 'Phase 5: Full Fleet Rollout',
            'description': 'Scale to entire GPU fleet with automation (Weeks 19-24)',
            'due_on': (start_date + timedelta(weeks=24)).isoformat(),
        },
        {
            'title': 'Phase 6: Continuous Improvement',
            'description': 'Refine models and expand capabilities (Ongoing)',
            'due_on': None,
        },
    ]
    
    print("\nCreating milestones...")
    milestone_numbers = {}
    for milestone in milestones:
        try:
            payload = {
                'title': milestone['title'],
                'description': milestone['description'],
                'state': 'open'
            }
            if milestone['due_on']:
                payload['due_on'] = milestone['due_on']
            
            response = requests.post(
                f'{API_BASE}/milestones',
                headers=headers,
                json=payload
            )
            if response.status_code == 201:
                data = response.json()
                milestone_numbers[milestone['title']] = data['number']
                print(f"✓ Created milestone: {milestone['title']} (#{data['number']})")
            else:
                print(f"✗ Failed to create milestone {milestone['title']}: {response.status_code}")
        except Exception as e:
            print(f"✗ Error creating milestone {milestone['title']}: {e}")
    
    return milestone_numbers

def create_issues(milestone_numbers):
    """Create all project issues"""
    
    issues = [
        # ============================================================================
        # PHASE 1: FOUNDATION (Weeks 1-4)
        # ============================================================================
        {
            'title': '[EPIC] Core Telemetry Pipeline',
            'body': '''## Epic Overview
Establish end-to-end data collection pipeline from GPU hardware to storage layer.

## Goals
- Collect 100+ metrics per GPU every 10 seconds
- 99.9% collection success rate
- < 30s end-to-end latency

## Components
- DCGM exporters on GPU hosts
- Kafka message queue
- Stream processors
- TimescaleDB storage

## Success Criteria
- [ ] 100 pilot GPUs reporting metrics
- [ ] Data flowing through entire pipeline
- [ ] Basic monitoring dashboards operational
- [ ] Metrics validated against DCGM sources

## Related Issues
This epic tracks the foundation infrastructure for the entire system.
''',
            'labels': ['epic', 'infrastructure', 'P0-critical'],
            'milestone': 'Phase 1: Foundation',
        },
        {
            'title': '[Infrastructure] Deploy DCGM Exporters on GPU Hosts',
            'body': '''## User Story
As a system operator, I want DCGM exporters deployed on all GPU hosts so that hardware metrics are collected continuously.

## Description
Deploy and configure NVIDIA DCGM exporters on 100 pilot GPU hosts to collect hardware telemetry.

## Acceptance Criteria
- [ ] DCGM exporter installed on all 100 pilot GPU hosts
- [ ] Exporters configured to collect metrics every 10 seconds
- [ ] Metrics endpoint accessible on port 9400
- [ ] All GPUs discovered and reporting
- [ ] Automatic restart on failure configured

## Technical Tasks
- [ ] Create DCGM exporter Docker image
- [ ] Write deployment script for batch installation
- [ ] Configure systemd service for auto-restart
- [ ] Verify metrics endpoint on each host
- [ ] Document deployment procedure

## Dependencies
- Requires: Access to GPU hosts
- Blocks: #2 (Kafka ingestion)

## Story Points: 5
''',
            'labels': ['feature', 'infrastructure', 'P0-critical'],
            'milestone': 'Phase 1: Foundation',
        },
        {
            'title': '[Infrastructure] Set Up Kafka Cluster',
            'body': '''## User Story
As a data engineer, I want a Kafka cluster operational so that GPU metrics can be streamed reliably.

## Description
Deploy production-grade Kafka cluster with Zookeeper for metric ingestion and stream processing.

## Acceptance Criteria
- [ ] 3-broker Kafka cluster deployed
- [ ] Zookeeper ensemble configured
- [ ] Topics created: gpu-metrics-raw, gpu-metrics-validated, gpu-alerts
- [ ] Retention policy: 7 days
- [ ] Replication factor: 2
- [ ] Monitoring with JMX metrics

## Technical Tasks
- [ ] Deploy Kafka cluster using Docker Compose
- [ ] Configure Zookeeper ensemble (3 nodes)
- [ ] Create required topics with partitioning
- [ ] Set up retention and compaction policies
- [ ] Configure producer/consumer ACLs
- [ ] Test throughput and latency
- [ ] Document cluster configuration

## Dependencies
- Blocks: #3 (Stream processor)

## Story Points: 8
''',
            'labels': ['feature', 'infrastructure', 'data-pipeline', 'P0-critical'],
            'milestone': 'Phase 1: Foundation',
        },
        {
            'title': '[Backend] Implement Metric Collection Agents',
            'body': '''## User Story
As a developer, I want collection agents to scrape DCGM metrics and publish to Kafka so that data flows into the pipeline.

## Description
Develop Go-based collection agents that scrape DCGM exporters and publish to Kafka with enrichment.

## Acceptance Criteria
- [ ] Agent scrapes DCGM exporter every 10 seconds
- [ ] Metrics enriched with GPU metadata (location, age, model)
- [ ] Schema validation before publishing
- [ ] Local buffering for network failures
- [ ] Configurable via YAML file
- [ ] Graceful shutdown handling

## Technical Tasks
- [ ] Implement DCGM metric scraper in Go
- [ ] Add metadata enrichment from config
- [ ] Implement Kafka producer with retry logic
- [ ] Add local disk buffer for offline queuing
- [ ] Write unit tests (>80% coverage)
- [ ] Create configuration template
- [ ] Document agent architecture

## Dependencies
- Requires: #1 (DCGM exporters), #2 (Kafka)

## Story Points: 13
''',
            'labels': ['feature', 'backend', 'data-pipeline', 'P0-critical'],
            'milestone': 'Phase 1: Foundation',
        },
        {
            'title': '[Database] Deploy TimescaleDB for Time-Series Storage',
            'body': '''## User Story
As a data engineer, I want TimescaleDB deployed so that we can store GPU metrics efficiently.

## Description
Deploy TimescaleDB with replication and configure hypertables for metric storage.

## Acceptance Criteria
- [ ] TimescaleDB 2.x deployed with PostgreSQL 15
- [ ] Primary and replica nodes configured
- [ ] Hypertable created for gpu_health_metrics
- [ ] Automatic partitioning by time (1 day chunks)
- [ ] Continuous aggregates for 1min/1hour windows
- [ ] Retention policy: 90 days full resolution
- [ ] Backup strategy documented

## Technical Tasks
- [ ] Deploy TimescaleDB via Docker
- [ ] Create database schema (see architecture doc)
- [ ] Convert tables to hypertables
- [ ] Create continuous aggregates
- [ ] Set up replication to standby
- [ ] Configure retention policies
- [ ] Test insert performance (target: 50k inserts/sec)
- [ ] Document schema and indexes

## Dependencies
- Blocks: #5 (Stream processor)

## Story Points: 8
''',
            'labels': ['feature', 'database', 'infrastructure', 'P1-high'],
            'milestone': 'Phase 1: Foundation',
        },
        {
            'title': '[Backend] Build Stream Processor for Kafka to Database',
            'body': '''## User Story
As a developer, I want a stream processor to consume Kafka metrics and write to TimescaleDB.

## Description
Implement Kafka Streams or Python consumer to process metrics and batch-insert into database.

## Acceptance Criteria
- [ ] Consumes from gpu-metrics-raw topic
- [ ] Validates metric schema
- [ ] Batch writes to TimescaleDB (100 rows/batch)
- [ ] Handles backpressure gracefully
- [ ] Exactly-once delivery semantics
- [ ] Monitoring via Prometheus metrics
- [ ] Can replay from specific offset

## Technical Tasks
- [ ] Implement Kafka consumer in Python
- [ ] Add schema validation with Pydantic
- [ ] Implement batch insert with psycopg2
- [ ] Add error handling and dead letter queue
- [ ] Implement Prometheus metrics
- [ ] Write integration tests
- [ ] Document processing guarantees

## Dependencies
- Requires: #2 (Kafka), #4 (TimescaleDB)

## Story Points: 13
''',
            'labels': ['feature', 'backend', 'data-pipeline', 'P0-critical'],
            'milestone': 'Phase 1: Foundation',
        },
        {
            'title': '[Database] Create PostgreSQL Asset Database',
            'body': '''## User Story
As a system operator, I want an asset database to track GPU inventory and metadata.

## Description
Deploy PostgreSQL database for GPU asset management with full schema implementation.

## Acceptance Criteria
- [ ] PostgreSQL 15+ deployed
- [ ] Schema created: gpu_assets, datacenters, hosts
- [ ] All 100 pilot GPUs registered
- [ ] Foreign key constraints implemented
- [ ] Indexes on frequently queried columns
- [ ] Backup strategy in place

## Technical Tasks
- [ ] Deploy PostgreSQL via Docker
- [ ] Create complete schema from architecture doc
- [ ] Write data migration script for GPU inventory
- [ ] Create indexes (status, datacenter, deployed_date)
- [ ] Set up automated backups
- [ ] Document schema relationships

## Dependencies
- None

## Story Points: 5
''',
            'labels': ['feature', 'database', 'P1-high'],
            'milestone': 'Phase 1: Foundation',
        },
        {
            'title': '[Monitoring] Deploy Grafana with Initial Dashboards',
            'body': '''## User Story
As an operator, I want Grafana dashboards so I can visualize GPU metrics in real-time.

## Description
Deploy Grafana and create initial dashboards for temperature, utilization, and ECC errors.

## Acceptance Criteria
- [ ] Grafana deployed and accessible
- [ ] TimescaleDB connected as data source
- [ ] Dashboard 1: Fleet Overview (temp, power, util)
- [ ] Dashboard 2: GPU Deep Dive (individual GPU metrics)
- [ ] Dashboard 3: ECC Errors (correctable/uncorrectable)
- [ ] Auto-refresh every 30 seconds
- [ ] Dashboards exported as JSON

## Technical Tasks
- [ ] Deploy Grafana via Docker
- [ ] Configure TimescaleDB data source
- [ ] Create fleet overview dashboard
- [ ] Create per-GPU drill-down dashboard
- [ ] Create ECC error tracking dashboard
- [ ] Add alerting for critical thresholds
- [ ] Document dashboard usage

## Dependencies
- Requires: #4 (TimescaleDB)

## Story Points: 5
''',
            'labels': ['feature', 'frontend', 'monitoring', 'P2-medium'],
            'milestone': 'Phase 1: Foundation',
        },
        {
            'title': '[Infrastructure] Implement End-to-End Pipeline Testing',
            'body': '''## User Story
As a QA engineer, I want end-to-end tests to verify data flows correctly through the entire pipeline.

## Description
Create integration tests that validate metrics flow from DCGM through to database.

## Acceptance Criteria
- [ ] Test publishes sample metrics to DCGM exporter
- [ ] Verifies metrics appear in Kafka
- [ ] Confirms metrics written to TimescaleDB
- [ ] Validates data integrity (no loss)
- [ ] Measures end-to-end latency (<30s target)
- [ ] Tests run in CI/CD pipeline

## Technical Tasks
- [ ] Write integration test script in Python
- [ ] Create test data fixtures
- [ ] Implement Kafka consumer for verification
- [ ] Query TimescaleDB to verify writes
- [ ] Add latency measurements
- [ ] Integrate with GitHub Actions CI
- [ ] Document test procedures

## Dependencies
- Requires: #1, #2, #3, #4, #5

## Story Points: 8
''',
            'labels': ['feature', 'infrastructure', 'P1-high'],
            'milestone': 'Phase 1: Foundation',
        },
        {
            'title': '[Documentation] Phase 1 Deployment Guide',
            'body': '''## User Story
As a new team member, I want deployment documentation so I can set up the infrastructure.

## Description
Write comprehensive deployment guide covering all Phase 1 components.

## Acceptance Criteria
- [ ] Prerequisites documented (hardware, software)
- [ ] Step-by-step deployment instructions
- [ ] Configuration file examples
- [ ] Troubleshooting guide
- [ ] Architecture diagrams updated
- [ ] Runbook for common operations

## Technical Tasks
- [ ] Document DCGM exporter deployment
- [ ] Document Kafka setup and configuration
- [ ] Document database deployment
- [ ] Write troubleshooting section
- [ ] Create operations runbook
- [ ] Add architecture diagrams

## Story Points: 5
''',
            'labels': ['documentation', 'P2-medium'],
            'milestone': 'Phase 1: Foundation',
        },
        
        # ============================================================================
        # PHASE 2: HEALTH SCORING (Weeks 5-8)
        # ============================================================================
        {
            'title': '[EPIC] Multi-Dimensional Health Scoring',
            'body': '''## Epic Overview
Implement comprehensive GPU health scoring system with 5 dimensions.

## Goals
- Calculate health scores (0-100) for all GPUs
- Scores updated every 15 minutes
- 5 sub-scores: thermal, memory, power, performance, reliability

## Components
- Health scoring engine
- Score calculation algorithms
- Historical tracking
- Alert generation
- Health dashboard

## Success Criteria
- [ ] Health scores calculated for all pilot GPUs
- [ ] Scores validated against known good/bad GPUs
- [ ] Alert system detecting degradation within 5 minutes
- [ ] API endpoints for health queries

## Related Issues
Builds on Phase 1 infrastructure.
''',
            'labels': ['epic', 'backend', 'P0-critical'],
            'milestone': 'Phase 2: Health Scoring',
        },
        {
            'title': '[Backend] Implement Thermal Health Scoring Algorithm',
            'body': '''## User Story
As a developer, I want thermal health scoring implemented so we can track temperature-related degradation.

## Description
Implement thermal health scoring based on temperature metrics and throttling events.

## Acceptance Criteria
- [ ] Algorithm calculates thermal score (0-100)
- [ ] Considers avg temp, max temp, throttle events
- [ ] Penalties: throttling (-10), high temp (-5)
- [ ] Score updated every 15 minutes
- [ ] Unit tests with edge cases

## Technical Tasks
- [ ] Implement thermal_health_score() function
- [ ] Query 7-day temperature stats from TimescaleDB
- [ ] Count throttle events in 24h window
- [ ] Calculate penalties per architecture doc
- [ ] Write unit tests (>90% coverage)
- [ ] Document scoring logic

## Dependencies
- Requires: Phase 1 complete

## Story Points: 5
''',
            'labels': ['feature', 'backend', 'P0-critical'],
            'milestone': 'Phase 2: Health Scoring',
        },
        {
            'title': '[Backend] Implement Memory Health Scoring Algorithm',
            'body': '''## User Story
As a developer, I want memory health scoring to track ECC errors and bandwidth degradation.

## Description
Implement memory health scoring with focus on ECC errors (highest predictive power).

## Acceptance Criteria
- [ ] Algorithm calculates memory score (0-100)
- [ ] Tracks correctable and uncorrectable ECC errors
- [ ] Cap score at 70 if any uncorrectable errors in 7d
- [ ] Bandwidth degradation penalties
- [ ] Score updated every 15 minutes

## Technical Tasks
- [ ] Implement memory_health_score() function
- [ ] Query ECC error counts from TimescaleDB
- [ ] Implement bandwidth degradation checks
- [ ] Apply critical rules (uncorrectable errors)
- [ ] Write comprehensive unit tests
- [ ] Document scoring rules

## Dependencies
- Requires: Phase 1 complete

## Story Points: 8
''',
            'labels': ['feature', 'backend', 'P0-critical'],
            'milestone': 'Phase 2: Health Scoring',
        },
        {
            'title': '[Backend] Implement Power, Performance, and Reliability Scoring',
            'body': '''## User Story
As a developer, I want the remaining health dimensions implemented to complete the scoring system.

## Description
Implement power, performance, and reliability health scoring algorithms.

## Acceptance Criteria
- [ ] Power health: variance, violations, efficiency
- [ ] Performance health: throughput, clock stability
- [ ] Reliability health: uptime, job success rate
- [ ] All three scores (0-100) calculated every 15min
- [ ] Unit tests for all algorithms

## Technical Tasks
- [ ] Implement power_health_score() function
- [ ] Implement performance_health_score() function
- [ ] Implement reliability_health_score() function
- [ ] Query relevant metrics from TimescaleDB
- [ ] Write unit tests for each
- [ ] Document scoring formulas

## Dependencies
- Requires: Phase 1 complete

## Story Points: 8
''',
            'labels': ['feature', 'backend', 'P1-high'],
            'milestone': 'Phase 2: Health Scoring',
        },
        {
            'title': '[Backend] Build Overall Health Score Aggregator',
            'body': '''## User Story
As a developer, I want overall health scores calculated from sub-scores.

## Description
Implement weighted aggregation of 5 health dimensions into overall score.

## Acceptance Criteria
- [ ] Weighted average: memory 30%, thermal 25%, performance 20%, power 15%, reliability 10%
- [ ] Overall score (0-100) calculated
- [ ] Trend analysis (-10 to +10)
- [ ] Risk level classification (low/medium/high/critical)
- [ ] Scores stored in database

## Technical Tasks
- [ ] Implement calculate_overall_score() function
- [ ] Calculate 7-day and 30-day trends
- [ ] Classify risk levels
- [ ] Store in gpu_health_scores table
- [ ] Write unit tests
- [ ] Document aggregation logic

## Dependencies
- Requires: #11, #12, #13

## Story Points: 5
''',
            'labels': ['feature', 'backend', 'P0-critical'],
            'milestone': 'Phase 2: Health Scoring',
        },
        {
            'title': '[Backend] Create Health Scoring Service',
            'body': '''## User Story
As an operator, I want health scores calculated automatically every 15 minutes.

## Description
Create background service that runs health scoring for all GPUs on schedule.

## Acceptance Criteria
- [ ] Service runs every 15 minutes
- [ ] Processes all active GPUs
- [ ] Writes scores to database
- [ ] Handles failures gracefully
- [ ] Prometheus metrics for monitoring
- [ ] Configurable via environment variables

## Technical Tasks
- [ ] Create Python service with APScheduler
- [ ] Implement main scoring loop
- [ ] Add error handling and retries
- [ ] Export Prometheus metrics
- [ ] Containerize with Docker
- [ ] Create systemd service file
- [ ] Document configuration options

## Dependencies
- Requires: #11, #12, #13, #14

## Story Points: 8
''',
            'labels': ['feature', 'backend', 'P0-critical'],
            'milestone': 'Phase 2: Health Scoring',
        },
        {
            'title': '[Backend] Build Health Score REST API',
            'body': '''## User Story
As a frontend developer, I want REST API endpoints to query health scores.

## Description
Create FastAPI service exposing health score endpoints.

## Acceptance Criteria
- [ ] GET /api/v1/gpus/{gpu_id}/health - current score
- [ ] GET /api/v1/gpus/{gpu_id}/health/history - historical scores
- [ ] GET /api/v1/fleet/health - fleet summary
- [ ] GET /api/v1/fleet/degraded - list degraded GPUs
- [ ] OpenAPI documentation auto-generated
- [ ] Authentication with API keys
- [ ] Rate limiting implemented

## Technical Tasks
- [ ] Create FastAPI application
- [ ] Implement health query endpoints
- [ ] Add authentication middleware
- [ ] Implement rate limiting
- [ ] Write API tests
- [ ] Generate OpenAPI spec
- [ ] Document API usage

## Dependencies
- Requires: #15

## Story Points: 8
''',
            'labels': ['feature', 'backend', 'P1-high'],
            'milestone': 'Phase 2: Health Scoring',
        },
        {
            'title': '[Frontend] Build Health Score Dashboard',
            'body': '''## User Story
As an operator, I want a dashboard showing GPU health scores with drill-down capabilities.

## Description
Create Grafana dashboard displaying health scores with color-coding and drill-down.

## Acceptance Criteria
- [ ] Fleet overview with health distribution
- [ ] Color-coded health scores (green/yellow/orange/red)
- [ ] List of degraded GPUs (score < 70)
- [ ] Drill-down to individual GPU health trends
- [ ] All 5 sub-scores displayed
- [ ] Auto-refresh every 1 minute

## Technical Tasks
- [ ] Design dashboard layout
- [ ] Create PostgreSQL queries for health data
- [ ] Build fleet overview panel
- [ ] Build degraded GPU list panel
- [ ] Create drill-down panels
- [ ] Add color thresholds
- [ ] Export dashboard JSON

## Dependencies
- Requires: #15, #16

## Story Points: 8
''',
            'labels': ['feature', 'frontend', 'monitoring', 'P1-high'],
            'milestone': 'Phase 2: Health Scoring',
        },
        {
            'title': '[Backend] Implement Health Score Alerting',
            'body': '''## User Story
As an operator, I want alerts when GPUs show significant health degradation.

## Description
Implement alerting system that notifies on health score changes.

## Acceptance Criteria
- [ ] Alert when score drops below 70 (degraded)
- [ ] Alert when score drops >10 points in 24h
- [ ] Alert on uncorrectable ECC errors
- [ ] Configurable alert thresholds
- [ ] Multiple channels: email, Slack, PagerDuty
- [ ] Alert deduplication

## Technical Tasks
- [ ] Implement alert rule engine
- [ ] Add email notification support
- [ ] Add Slack webhook integration
- [ ] Add PagerDuty integration
- [ ] Implement alert deduplication
- [ ] Create alert configuration schema
- [ ] Document alerting setup

## Dependencies
- Requires: #15

## Story Points: 8
''',
            'labels': ['feature', 'backend', 'monitoring', 'P2-medium'],
            'milestone': 'Phase 2: Health Scoring',
        },
        {
            'title': '[Backend] Validate Health Scores Against Known Issues',
            'body': '''## User Story
As a QA engineer, I want to validate health scores against GPUs with known issues.

## Description
Compare calculated health scores against operator-reported problem GPUs.

## Acceptance Criteria
- [ ] Identify 10+ GPUs with known issues
- [ ] Calculate their health scores
- [ ] Verify low scores for problem GPUs
- [ ] Calculate accuracy metrics (precision/recall)
- [ ] Document validation results
- [ ] Adjust scoring algorithms if needed

## Technical Tasks
- [ ] Gather list of known problem GPUs
- [ ] Document their specific issues
- [ ] Run health scoring on these GPUs
- [ ] Compare scores to expected values
- [ ] Calculate validation metrics
- [ ] Create validation report
- [ ] Fine-tune algorithms based on results

## Dependencies
- Requires: #15

## Story Points: 5
''',
            'labels': ['feature', 'backend', 'P1-high'],
            'milestone': 'Phase 2: Health Scoring',
        },
        {
            'title': '[Documentation] Health Scoring System Documentation',
            'body': '''## User Story
As a team member, I want documentation explaining how health scoring works.

## Description
Comprehensive documentation of health scoring algorithms and interpretation.

## Acceptance Criteria
- [ ] All 5 health dimensions documented
- [ ] Scoring formulas explained
- [ ] Examples with sample data
- [ ] Interpretation guide (what scores mean)
- [ ] Troubleshooting common issues
- [ ] API documentation

## Technical Tasks
- [ ] Document thermal scoring algorithm
- [ ] Document memory scoring algorithm
- [ ] Document power/performance/reliability
- [ ] Create score interpretation guide
- [ ] Add examples and visualizations
- [ ] Document API endpoints

## Story Points: 5
''',
            'labels': ['documentation', 'P2-medium'],
            'milestone': 'Phase 2: Health Scoring',
        },
        
        # ============================================================================
        # PHASE 3: PREDICTIVE ANALYTICS (Weeks 9-14)
        # ============================================================================
        {
            'title': '[EPIC] Failure Prediction System',
            'body': '''## Epic Overview
Build ML-based failure prediction system with 7-90 day forecasting.

## Goals
- Predict failures 7-90 days in advance
- >85% accuracy for 30-day predictions
- <5% false positive rate
- Multiple model ensemble

## Components
- Feature engineering pipeline
- XGBoost failure classifier
- LSTM sequence model
- Model training pipeline
- Prediction API
- Monitoring dashboard

## Success Criteria
- [ ] Models trained with historical data
- [ ] Predictions generated daily
- [ ] >85% accuracy on validation set
- [ ] At least 1 failure predicted 7+ days early

## Related Issues
Core ML capabilities for the system.
''',
            'labels': ['epic', 'ml', 'P0-critical'],
            'milestone': 'Phase 3: Predictive Analytics',
        },
        {
            'title': '[ML] Collect and Label Historical Failure Data',
            'body': '''## User Story
As an ML engineer, I want historical failure data labeled so I can train prediction models.

## Description
Gather failure events from past 18-24 months and label failure types.

## Acceptance Criteria
- [ ] 100+ failure events collected
- [ ] Each failure labeled (memory/thermal/power/other)
- [ ] 6 months of pre-failure telemetry extracted
- [ ] Control set: 3x healthy GPUs per failure
- [ ] Data stored in ML-ready format
- [ ] Train/validation/test splits created

## Technical Tasks
- [ ] Query failure_events table for historical data
- [ ] Extract 6 months of metrics before each failure
- [ ] Label failure types with domain experts
- [ ] Extract equivalent periods from healthy GPUs
- [ ] Create balanced dataset with oversampling
- [ ] Split into train (60%) / val (20%) / test (20%)
- [ ] Document data collection methodology

## Dependencies
- Requires: Phase 2 complete

## Story Points: 13
''',
            'labels': ['feature', 'ml', 'data-pipeline', 'P0-critical'],
            'milestone': 'Phase 3: Predictive Analytics',
        },
        {
            'title': '[ML] Build Feature Engineering Pipeline',
            'body': '''## User Story
As an ML engineer, I want a feature engineering pipeline to create 200+ features from raw metrics.

## Description
Build automated pipeline that extracts predictive features from GPU telemetry.

## Acceptance Criteria
- [ ] 200+ features extracted per GPU
- [ ] Time-series features: rolling stats (7d, 30d)
- [ ] Statistical features: percentiles, variance
- [ ] Trend features: slopes, acceleration
- [ ] Anomaly features: event counts
- [ ] Features stored in Feast feature store
- [ ] Pipeline runs daily

## Technical Tasks
- [ ] Implement rolling statistics (mean, std, max, min)
- [ ] Calculate temperature percentiles (p50, p90, p95, p99)
- [ ] Compute trend slopes via linear regression
- [ ] Count anomaly events (throttling, power violations)
- [ ] Calculate ECC error rates and trends
- [ ] Set up Feast feature store
- [ ] Create feature documentation
- [ ] Write feature engineering tests

## Dependencies
- Requires: #21

## Story Points: 13
''',
            'labels': ['feature', 'ml', 'data-pipeline', 'P0-critical'],
            'milestone': 'Phase 3: Predictive Analytics',
        },
        {
            'title': '[ML] Train XGBoost Failure Classifier',
            'body': '''## User Story
As an ML engineer, I want an XGBoost model that predicts 30-day failure probability.

## Description
Train gradient boosting model for binary failure classification.

## Acceptance Criteria
- [ ] Model trained on labeled dataset
- [ ] AUC >0.85 on validation set
- [ ] <5% false positive rate
- [ ] Feature importance analysis documented
- [ ] Hyperparameters tuned via grid search
- [ ] Model versioned in MLflow
- [ ] Training pipeline automated

## Technical Tasks
- [ ] Implement XGBoost training script
- [ ] Perform hyperparameter tuning
- [ ] Handle class imbalance (scale_pos_weight)
- [ ] Calculate evaluation metrics (AUC, precision, recall)
- [ ] Analyze feature importance
- [ ] Save model to MLflow registry
- [ ] Create model card documentation
- [ ] Write model unit tests

## Dependencies
- Requires: #21, #22

## Story Points: 13
''',
            'labels': ['feature', 'ml', 'P0-critical'],
            'milestone': 'Phase 3: Predictive Analytics',
        },
        {
            'title': '[ML] Train LSTM Sequence Model',
            'body': '''## User Story
As an ML engineer, I want an LSTM model to capture time-series patterns in GPU degradation.

## Description
Build PyTorch LSTM model for sequence-based failure prediction.

## Acceptance Criteria
- [ ] LSTM architecture designed (2-3 layers)
- [ ] Trained on 30-day sequences
- [ ] Predicts failure probability and type
- [ ] Validation accuracy >80%
- [ ] Model saved in ONNX format
- [ ] Inference latency <100ms

## Technical Tasks
- [ ] Design LSTM architecture
- [ ] Implement data loader for sequences
- [ ] Train model with PyTorch
- [ ] Implement early stopping
- [ ] Evaluate on validation set
- [ ] Export to ONNX format
- [ ] Benchmark inference performance
- [ ] Document model architecture

## Dependencies
- Requires: #21, #22

## Story Points: 13
''',
            'labels': ['feature', 'ml', 'P1-high'],
            'milestone': 'Phase 3: Predictive Analytics',
        },
        {
            'title': '[ML] Implement Isolation Forest for Anomaly Detection',
            'body': '''## User Story
As an ML engineer, I want anomaly detection to catch novel failure modes not in training data.

## Description
Train Isolation Forest model to detect unusual GPU behavior patterns.

## Acceptance Criteria
- [ ] Model trained on healthy GPU data
- [ ] Anomaly score (0-1) calculated
- [ ] Detects outliers not seen in training
- [ ] Integrated with prediction pipeline
- [ ] False positive rate <10%

## Technical Tasks
- [ ] Train Isolation Forest on healthy data
- [ ] Tune contamination parameter
- [ ] Implement scoring function
- [ ] Evaluate on known anomalies
- [ ] Integrate with prediction service
- [ ] Document anomaly interpretation

## Dependencies
- Requires: #22

## Story Points: 8
''',
            'labels': ['feature', 'ml', 'P2-medium'],
            'milestone': 'Phase 3: Predictive Analytics',
        },
        {
            'title': '[Backend] Build Model Serving Infrastructure',
            'body': '''## User Story
As a developer, I want ML models served via API for real-time predictions.

## Description
Deploy Ray Serve infrastructure for scalable model inference.

## Acceptance Criteria
- [ ] Ray Serve cluster deployed
- [ ] Models loaded from MLflow registry
- [ ] REST API for predictions
- [ ] Batch prediction support
- [ ] Auto-scaling based on load
- [ ] <100ms p95 latency
- [ ] Prometheus metrics exported

## Technical Tasks
- [ ] Deploy Ray Serve cluster
- [ ] Create model serving classes
- [ ] Implement REST API endpoints
- [ ] Add model versioning support
- [ ] Configure auto-scaling
- [ ] Add monitoring and metrics
- [ ] Load test inference performance
- [ ] Document API usage

## Dependencies
- Requires: #23, #24

## Story Points: 13
''',
            'labels': ['feature', 'backend', 'ml', 'infrastructure', 'P0-critical'],
            'milestone': 'Phase 3: Predictive Analytics',
        },
        {
            'title': '[Backend] Create Daily Prediction Job',
            'body': '''## User Story
As an operator, I want predictions generated daily for all GPUs automatically.

## Description
Build scheduled job that generates failure predictions for entire fleet.

## Acceptance Criteria
- [ ] Job runs daily at specified time
- [ ] Processes all active GPUs
- [ ] Calls feature engineering pipeline
- [ ] Invokes model serving API
- [ ] Stores predictions in database
- [ ] Sends alerts for high-risk GPUs
- [ ] Job monitoring via Prometheus

## Technical Tasks
- [ ] Create prediction job script
- [ ] Implement batch processing logic
- [ ] Query feature store for latest features
- [ ] Call prediction API in batches
- [ ] Store results in gpu_predictions table
- [ ] Trigger alerts for critical predictions
- [ ] Add job monitoring
- [ ] Document job configuration

## Dependencies
- Requires: #26

## Story Points: 8
''',
            'labels': ['feature', 'backend', 'ml', 'P0-critical'],
            'milestone': 'Phase 3: Predictive Analytics',
        },
        {
            'title': '[Backend] Build Prediction API Endpoints',
            'body': '''## User Story
As a developer, I want API endpoints to query failure predictions.

## Description
Extend REST API with prediction query endpoints.

## Acceptance Criteria
- [ ] GET /api/v1/gpus/{gpu_id}/prediction - current prediction
- [ ] GET /api/v1/gpus/{gpu_id}/prediction/history - historical
- [ ] GET /api/v1/fleet/at-risk - list high-risk GPUs
- [ ] GET /api/v1/predictions/accuracy - model performance metrics
- [ ] Supports filtering by risk level
- [ ] OpenAPI documentation updated

## Technical Tasks
- [ ] Implement prediction query endpoints
- [ ] Add filtering and pagination
- [ ] Create model performance endpoint
- [ ] Update OpenAPI spec
- [ ] Write API tests
- [ ] Document endpoint usage

## Dependencies
- Requires: #27

## Story Points: 5
''',
            'labels': ['feature', 'backend', 'P1-high'],
            'milestone': 'Phase 3: Predictive Analytics',
        },
        {
            'title': '[Frontend] Build Prediction Dashboard',
            'body': '''## User Story
As an operator, I want a dashboard showing GPU failure predictions and risk levels.

## Description
Create Grafana dashboard for failure predictions with risk visualization.

## Acceptance Criteria
- [ ] Risk distribution chart (low/med/high/critical)
- [ ] List of top 20 at-risk GPUs
- [ ] Prediction timeline (7/30/90 day)
- [ ] Model performance metrics
- [ ] Historical prediction accuracy
- [ ] Drill-down to individual GPU predictions

## Technical Tasks
- [ ] Design dashboard layout
- [ ] Create risk distribution visualization
- [ ] Build at-risk GPU table
- [ ] Add prediction timeline chart
- [ ] Display model accuracy metrics
- [ ] Create drill-down panels
- [ ] Export dashboard JSON

## Dependencies
- Requires: #27, #28

## Story Points: 8
''',
            'labels': ['feature', 'frontend', 'monitoring', 'P1-high'],
            'milestone': 'Phase 3: Predictive Analytics',
        },
        {
            'title': '[ML] Implement Model Retraining Pipeline',
            'body': '''## User Story
As an ML engineer, I want models retrained weekly with new failure data.

## Description
Build automated pipeline for weekly model retraining with fresh data.

## Acceptance Criteria
- [ ] Pipeline fetches latest labeled failures
- [ ] Extracts new features
- [ ] Retrains all models
- [ ] Evaluates on validation set
- [ ] A/B tests against production model
- [ ] Promotes if performance improves
- [ ] Runs every Sunday at midnight

## Technical Tasks
- [ ] Create retraining orchestration script
- [ ] Implement data fetching logic
- [ ] Add model training step
- [ ] Implement A/B testing framework
- [ ] Add model promotion logic
- [ ] Schedule with cron or Airflow
- [ ] Add monitoring and alerts
- [ ] Document retraining process

## Dependencies
- Requires: #23, #24

## Story Points: 13
''',
            'labels': ['feature', 'ml', 'infrastructure', 'P2-medium'],
            'milestone': 'Phase 3: Predictive Analytics',
        },
        {
            'title': '[Documentation] ML Model Documentation',
            'body': '''## User Story
As a data scientist, I want documentation explaining model architectures and performance.

## Description
Comprehensive ML documentation including model cards and usage guides.

## Acceptance Criteria
- [ ] Model cards for XGBoost, LSTM, Isolation Forest
- [ ] Feature importance analysis
- [ ] Performance metrics and benchmarks
- [ ] Prediction interpretation guide
- [ ] API usage examples
- [ ] Troubleshooting guide

## Technical Tasks
- [ ] Create model cards for each model
- [ ] Document feature engineering
- [ ] Add performance benchmark results
- [ ] Write prediction interpretation guide
- [ ] Create API usage examples
- [ ] Document retraining process

## Story Points: 5
''',
            'labels': ['documentation', 'ml', 'P2-medium'],
            'milestone': 'Phase 3: Predictive Analytics',
        },
        
        # ============================================================================
        # PHASE 4: ECONOMIC ENGINE (Weeks 15-18)
        # ============================================================================
        {
            'title': '[EPIC] Economic Decision Engine',
            'body': '''## Epic Overview
Build economic decision-making framework for GPU lifecycle management.

## Goals
- Calculate residual value for all GPUs
- Recommend keep/sell/repurpose/decommission
- Integrate with secondary market pricing
- Demonstrate ROI from system

## Components
- Residual value calculator
- Operational cost projector
- Revenue estimator
- Decision matrix
- Economic dashboard
- Pricing API

## Success Criteria
- [ ] Economic recommendations for all pilot GPUs
- [ ] Residual value estimates within 15% of actual
- [ ] 3+ GPUs sold via recommendations
- [ ] Positive ROI demonstrated

## Related Issues
Business value layer of the system.
''',
            'labels': ['epic', 'backend', 'P1-high'],
            'milestone': 'Phase 4: Economic Engine',
        },
        {
            'title': '[Backend] Implement Residual Value Calculator',
            'body': '''## User Story
As a finance analyst, I want GPU residual values calculated automatically.

## Description
Build calculator that estimates current market value based on health, age, and demand.

## Acceptance Criteria
- [ ] Base value from market pricing API
- [ ] Age depreciation factor (50% over 5 years)
- [ ] Health multiplier (0.5 - 1.2)
- [ ] Market demand adjustment
- [ ] Warranty value addition
- [ ] Prices bounded by salvage and new price

## Technical Tasks
- [ ] Implement calculate_residual_value() function
- [ ] Integrate market pricing API (or mock)
- [ ] Calculate depreciation curves
- [ ] Apply health multipliers
- [ ] Add warranty calculations
- [ ] Write unit tests with examples
- [ ] Document pricing formulas

## Dependencies
- Requires: Phase 2 complete (health scores)

## Story Points: 8
''',
            'labels': ['feature', 'backend', 'P1-high'],
            'milestone': 'Phase 4: Economic Engine',
        },
        {
            'title': '[Backend] Build Operational Cost Projector',
            'body': '''## User Story
As an analyst, I want projected operational costs for the next 12 months.

## Description
Calculate ongoing costs: power, cooling, maintenance, risk, rack space.

## Acceptance Criteria
- [ ] Power cost based on average draw
- [ ] Cooling cost (0.3x power cost)
- [ ] Maintenance cost with health penalty
- [ ] Risk cost from failure probability
- [ ] Monthly and annual projections
- [ ] Configurable cost parameters

## Technical Tasks
- [ ] Implement project_operational_costs() function
- [ ] Calculate power costs from metrics
- [ ] Add cooling cost multiplier
- [ ] Implement health-based maintenance costs
- [ ] Calculate risk costs from predictions
- [ ] Add configuration for cost parameters
- [ ] Write unit tests
- [ ] Document cost model

## Dependencies
- Requires: Phase 2 and 3 complete

## Story Points: 8
''',
            'labels': ['feature', 'backend', 'P1-high'],
            'milestone': 'Phase 4: Economic Engine',
        },
        {
            'title': '[Backend] Implement Revenue Potential Estimator',
            'body': '''## User Story
As an analyst, I want revenue projections based on GPU utilization and health.

## Description
Estimate revenue from GPU rental/usage based on health and market rates.

## Acceptance Criteria
- [ ] Market rate per hour by GPU model
- [ ] Utilization based on health score
- [ ] Availability factor from predictions
- [ ] Monthly and annual revenue projections
- [ ] Configurable hourly rates

## Technical Tasks
- [ ] Implement estimate_revenue_potential() function
- [ ] Query market rates (or configure defaults)
- [ ] Calculate utilization from health scores
- [ ] Factor in predicted downtime
- [ ] Project monthly and annual revenue
- [ ] Add configuration for rates
- [ ] Write unit tests
- [ ] Document revenue model

## Dependencies
- Requires: Phase 2 and 3 complete

## Story Points: 5
''',
            'labels': ['feature', 'backend', 'P1-high'],
            'milestone': 'Phase 4: Economic Engine',
        },
        {
            'title': '[Backend] Build Economic Decision Matrix',
            'body': '''## User Story
As a manager, I want data-driven recommendations on GPU lifecycle actions.

## Description
Implement decision logic that recommends keep/sell/repurpose/decommission based on NPV.

## Acceptance Criteria
- [ ] NPV calculated for each action
- [ ] Decision selects highest NPV
- [ ] Safety overrides (health < 40 = decommission)
- [ ] Confidence scores calculated
- [ ] Alternative options provided
- [ ] Decisions stored in database

## Technical Tasks
- [ ] Implement make_economic_decision() function
- [ ] Calculate NPV for each action
- [ ] Implement decision logic from architecture doc
- [ ] Add safety override rules
- [ ] Calculate confidence scores
- [ ] Store in economic_decisions table
- [ ] Write comprehensive unit tests
- [ ] Document decision rules

## Dependencies
- Requires: #33, #34, #35

## Story Points: 8
''',
            'labels': ['feature', 'backend', 'P0-critical'],
            'milestone': 'Phase 4: Economic Engine',
        },
        {
            'title': '[Backend] Create Secondary Market Pricing Calculator',
            'body': '''## User Story
As a sales analyst, I want recommended pricing for GPUs being sold in secondary market.

## Description
Calculate optimal listing price, minimum acceptable, and target price.

## Acceptance Criteria
- [ ] List price with health adjustment
- [ ] Demand multiplier from market data
- [ ] Urgency discount for quick sales
- [ ] Bulk discount for multiple units
- [ ] Min/target prices calculated
- [ ] Pricing factors documented

## Technical Tasks
- [ ] Implement calculate_secondary_market_price() function
- [ ] Apply health factor to base price
- [ ] Integrate demand data (or mock)
- [ ] Add urgency and bulk discounts
- [ ] Calculate min and target prices
- [ ] Write unit tests with examples
- [ ] Document pricing strategy

## Dependencies
- Requires: #33

## Story Points: 5
''',
            'labels': ['feature', 'backend', 'P2-medium'],
            'milestone': 'Phase 4: Economic Engine',
        },
        {
            'title': '[Backend] Build Economic Decision Service',
            'body': '''## User Story
As an operator, I want economic decisions calculated daily for all GPUs.

## Description
Create scheduled service that runs economic analysis on entire fleet.

## Acceptance Criteria
- [ ] Service runs daily
- [ ] Processes all active GPUs
- [ ] Stores decisions in database
- [ ] Generates alerts for high-value recommendations
- [ ] Exports metrics to Prometheus
- [ ] Configurable decision parameters

## Technical Tasks
- [ ] Create economic decision service
- [ ] Implement daily scheduling
- [ ] Query health scores and predictions
- [ ] Run decision logic for each GPU
- [ ] Store results in database
- [ ] Generate alerts for critical decisions
- [ ] Add monitoring metrics
- [ ] Document service configuration

## Dependencies
- Requires: #36

## Story Points: 8
''',
            'labels': ['feature', 'backend', 'P1-high'],
            'milestone': 'Phase 4: Economic Engine',
        },
        {
            'title': '[Backend] Extend API with Economic Endpoints',
            'body': '''## User Story
As a developer, I want API endpoints to query economic analysis results.

## Description
Add economic decision and pricing endpoints to REST API.

## Acceptance Criteria
- [ ] GET /api/v1/gpus/{gpu_id}/economic - economic analysis
- [ ] GET /api/v1/gpus/{gpu_id}/pricing - secondary market price
- [ ] GET /api/v1/fleet/recommendations - fleet-wide recommendations
- [ ] GET /api/v1/fleet/economics - fleet economic summary
- [ ] OpenAPI documentation updated

## Technical Tasks
- [ ] Implement economic query endpoints
- [ ] Add pricing endpoints
- [ ] Create fleet recommendation endpoint
- [ ] Build fleet economics summary
- [ ] Update OpenAPI spec
- [ ] Write API tests
- [ ] Document endpoints

## Dependencies
- Requires: #38

## Story Points: 5
''',
            'labels': ['feature', 'backend', 'P1-high'],
            'milestone': 'Phase 4: Economic Engine',
        },
        {
            'title': '[Frontend] Build Economic Dashboard',
            'body': '''## User Story
As a manager, I want dashboards showing economic analysis and recommendations.

## Description
Create comprehensive economic dashboard with NPV analysis and recommendations.

## Acceptance Criteria
- [ ] Fleet asset valuation summary
- [ ] Monthly revenue and cost projections
- [ ] Recommendation distribution (keep/sell/etc)
- [ ] Top 10 candidates for sale
- [ ] ROI metrics from early detection
- [ ] Economic trend charts

## Technical Tasks
- [ ] Design dashboard layout
- [ ] Create asset valuation panel
- [ ] Build revenue/cost projection charts
- [ ] Add recommendation distribution
- [ ] Create sales candidate table
- [ ] Add ROI tracking metrics
- [ ] Export dashboard JSON

## Dependencies
- Requires: #38, #39

## Story Points: 8
''',
            'labels': ['feature', 'frontend', 'P1-high'],
            'milestone': 'Phase 4: Economic Engine',
        },
        {
            'title': '[Backend] Track Economic Decision Outcomes',
            'body': '''## User Story
As an analyst, I want to track whether economic recommendations were followed and their outcomes.

## Description
Build outcome tracking system to validate economic model accuracy.

## Acceptance Criteria
- [ ] Track decision execution (yes/no)
- [ ] Record actual sale prices
- [ ] Calculate variance from predictions
- [ ] Update decision records with outcomes
- [ ] Generate accuracy reports
- [ ] Feed outcomes back into model

## Technical Tasks
- [ ] Create outcome tracking schema
- [ ] Implement outcome recording API
- [ ] Calculate prediction accuracy
- [ ] Generate accuracy reports
- [ ] Build feedback loop for model improvement
- [ ] Document tracking process

## Dependencies
- Requires: #38

## Story Points: 8
''',
            'labels': ['feature', 'backend', 'P2-medium'],
            'milestone': 'Phase 4: Economic Engine',
        },
        {
            'title': '[Documentation] Economic Model Documentation',
            'body': '''## User Story
As a stakeholder, I want documentation explaining economic models and ROI calculations.

## Description
Comprehensive documentation of economic decision engine.

## Acceptance Criteria
- [ ] Residual value model explained
- [ ] Cost projection methodology
- [ ] Revenue estimation approach
- [ ] Decision matrix logic
- [ ] Pricing strategy documented
- [ ] ROI calculation examples

## Technical Tasks
- [ ] Document all economic models
- [ ] Add calculation examples
- [ ] Create decision flowcharts
- [ ] Document API endpoints
- [ ] Write interpretation guide
- [ ] Add troubleshooting section

## Story Points: 5
''',
            'labels': ['documentation', 'P2-medium'],
            'milestone': 'Phase 4: Economic Engine',
        },
        
        # ============================================================================
        # PHASE 5: FULL FLEET ROLLOUT (Weeks 19-24)
        # ============================================================================
        {
            'title': '[EPIC] Full Fleet Rollout',
            'body': '''## Epic Overview
Scale system to entire GPU fleet (10,000+ GPUs) with production-grade reliability.

## Goals
- Deploy to all 10,000+ GPUs
- 99.95% fleet reporting health metrics
- <1% false positive rate on alerts
- >80% prediction accuracy validated
- Demonstrable ROI

## Components
- Kubernetes deployment
- Multi-region infrastructure
- Auto-scaling
- Operator training
- Integration with asset management
- Production monitoring

## Success Criteria
- [ ] 99.95% of fleet reporting
- [ ] All services auto-scaling
- [ ] Operators trained and certified
- [ ] ROI documented and validated

## Related Issues
Production deployment and operationalization.
''',
            'labels': ['epic', 'infrastructure', 'P0-critical'],
            'milestone': 'Phase 5: Full Fleet Rollout',
        },
        {
            'title': '[Infrastructure] Deploy Kubernetes Cluster',
            'body': '''## User Story
As a DevOps engineer, I want Kubernetes cluster deployed for production workloads.

## Description
Deploy production Kubernetes cluster with multi-node setup and auto-scaling.

## Acceptance Criteria
- [ ] Multi-node K8s cluster (10+ nodes)
- [ ] Horizontal pod autoscaling configured
- [ ] Persistent volumes for databases
- [ ] Load balancers for services
- [ ] Ingress controllers configured
- [ ] Monitoring with Prometheus operator

## Technical Tasks
- [ ] Deploy K8s cluster (managed or self-hosted)
- [ ] Configure node pools and auto-scaling
- [ ] Set up persistent storage class
- [ ] Deploy ingress controllers
- [ ] Install Prometheus operator
- [ ] Configure RBAC and namespaces
- [ ] Document cluster architecture

## Story Points: 13
''',
            'labels': ['feature', 'infrastructure', 'P0-critical'],
            'milestone': 'Phase 5: Full Fleet Rollout',
        },
        {
            'title': '[Infrastructure] Containerize All Services',
            'body': '''## User Story
As a DevOps engineer, I want all services containerized and K8s-ready.

## Description
Create production Docker images and Helm charts for all services.

## Acceptance Criteria
- [ ] Dockerfiles for all services optimized
- [ ] Multi-stage builds for smaller images
- [ ] Helm charts for each component
- [ ] ConfigMaps and Secrets management
- [ ] Health checks configured
- [ ] Resource limits defined

## Technical Tasks
- [ ] Create optimized Dockerfiles
- [ ] Build and tag images
- [ ] Push to container registry
- [ ] Create Helm charts
- [ ] Define resource requirements
- [ ] Add liveness/readiness probes
- [ ] Document deployment process

## Story Points: 13
''',
            'labels': ['feature', 'infrastructure', 'P0-critical'],
            'milestone': 'Phase 5: Full Fleet Rollout',
        },
        {
            'title': '[Infrastructure] Multi-Region Kafka Deployment',
            'body': '''## User Story
As a reliability engineer, I want Kafka deployed across multiple datacenters.

## Description
Deploy multi-region Kafka clusters with replication for high availability.

## Acceptance Criteria
- [ ] Kafka clusters in 3+ datacenters
- [ ] Cross-region replication configured
- [ ] MirrorMaker 2 for data sync
- [ ] Disaster recovery tested
- [ ] <5 minute failover time
- [ ] Monitoring across all regions

## Technical Tasks
- [ ] Deploy Kafka in each datacenter
- [ ] Configure MirrorMaker 2
- [ ] Set up monitoring federation
- [ ] Test failover scenarios
- [ ] Document DR procedures
- [ ] Create runbooks

## Story Points: 13
''',
            'labels': ['feature', 'infrastructure', 'data-pipeline', 'P1-high'],
            'milestone': 'Phase 5: Full Fleet Rollout',
        },
        {
            'title': '[Infrastructure] Scale TimescaleDB for Production',
            'body': '''## User Story
As a database admin, I want TimescaleDB scaled to handle 10,000+ GPUs.

## Description
Deploy production TimescaleDB cluster with read replicas and backup.

## Acceptance Criteria
- [ ] Primary-replica setup with auto-failover
- [ ] Connection pooling (PgBouncer)
- [ ] Continuous archival to object storage
- [ ] Point-in-time recovery tested
- [ ] Performance tuning completed
- [ ] Handles 500k+ inserts/sec

## Technical Tasks
- [ ] Deploy TimescaleDB cluster
- [ ] Configure streaming replication
- [ ] Set up PgBouncer connection pooler
- [ ] Implement backup strategy
- [ ] Tune PostgreSQL parameters
- [ ] Load test with production volumes
- [ ] Document scaling procedures

## Story Points: 13
''',
            'labels': ['feature', 'database', 'infrastructure', 'P0-critical'],
            'milestone': 'Phase 5: Full Fleet Rollout',
        },
        {
            'title': '[Infrastructure] Deploy Full Fleet DCGM Exporters',
            'body': '''## User Story
As an operator, I want DCGM exporters on all 10,000+ GPUs.

## Description
Roll out DCGM exporters and collection agents across entire fleet.

## Acceptance Criteria
- [ ] Exporters deployed to all GPU hosts
- [ ] Phased rollout: 1k → 5k → 10k GPUs
- [ ] Automated deployment via Ansible/Terraform
- [ ] Monitoring of deployment progress
- [ ] Rollback capability tested
- [ ] 99.95% deployment success

## Technical Tasks
- [ ] Create deployment automation
- [ ] Implement phased rollout plan
- [ ] Monitor deployment metrics
- [ ] Test rollback procedures
- [ ] Validate metrics collection
- [ ] Document deployment process

## Story Points: 13
''',
            'labels': ['feature', 'infrastructure', 'P0-critical'],
            'milestone': 'Phase 5: Full Fleet Rollout',
        },
        {
            'title': '[Backend] Implement Service Auto-Scaling',
            'body': '''## User Story
As a DevOps engineer, I want services to auto-scale based on load.

## Description
Configure HPA and cluster autoscaler for dynamic resource management.

## Acceptance Criteria
- [ ] HPA configured for all services
- [ ] Cluster autoscaler enabled
- [ ] Scale up/down based on CPU and custom metrics
- [ ] Min/max replicas defined
- [ ] Scale-down stabilization configured
- [ ] Tested with load scenarios

## Technical Tasks
- [ ] Configure Horizontal Pod Autoscalers
- [ ] Define custom metrics for scaling
- [ ] Set min/max replica counts
- [ ] Configure cluster autoscaler
- [ ] Load test scaling behavior
- [ ] Document scaling policies

## Story Points: 8
''',
            'labels': ['feature', 'infrastructure', 'P1-high'],
            'milestone': 'Phase 5: Full Fleet Rollout',
        },
        {
            'title': '[Backend] Asset Management System Integration',
            'body': '''## User Story
As an IT manager, I want GPU health data integrated with asset management.

## Description
Build API integration with existing asset management systems.

## Acceptance Criteria
- [ ] REST API for asset data sync
- [ ] Webhook notifications for status changes
- [ ] Bidirectional sync (health → assets, assets → health)
- [ ] Conflict resolution strategy
- [ ] Audit logging of changes
- [ ] API authentication implemented

## Technical Tasks
- [ ] Design integration API
- [ ] Implement asset sync endpoints
- [ ] Add webhook support
- [ ] Handle conflict resolution
- [ ] Add audit logging
- [ ] Write integration tests
- [ ] Document API usage

## Story Points: 13
''',
            'labels': ['feature', 'backend', 'P2-medium'],
            'milestone': 'Phase 5: Full Fleet Rollout',
        },
        {
            'title': '[Monitoring] Production Observability Stack',
            'body': '''## User Story
As an SRE, I want comprehensive monitoring for production system.

## Description
Deploy full observability stack: metrics, logs, traces, alerting.

## Acceptance Criteria
- [ ] Prometheus for metrics collection
- [ ] Grafana for visualization
- [ ] Loki or ELK for log aggregation
- [ ] Jaeger for distributed tracing
- [ ] Alertmanager for notifications
- [ ] Service dashboards for all components

## Technical Tasks
- [ ] Deploy Prometheus and Grafana
- [ ] Set up log aggregation
- [ ] Deploy tracing infrastructure
- [ ] Configure alerting rules
- [ ] Create service dashboards
- [ ] Set up on-call rotations
- [ ] Document monitoring architecture

## Story Points: 13
''',
            'labels': ['feature', 'monitoring', 'infrastructure', 'P0-critical'],
            'milestone': 'Phase 5: Full Fleet Rollout',
        },
        {
            'title': '[Documentation] Operator Training Program',
            'body': '''## User Story
As a training manager, I want comprehensive training for system operators.

## Description
Create training materials and conduct operator certification program.

## Acceptance Criteria
- [ ] Training manual created
- [ ] Video tutorials recorded
- [ ] Hands-on lab exercises
- [ ] Certification test developed
- [ ] 20+ operators trained and certified
- [ ] Training feedback incorporated

## Technical Tasks
- [ ] Write operator manual
- [ ] Create training slides
- [ ] Record video tutorials
- [ ] Design lab exercises
- [ ] Create certification test
- [ ] Conduct training sessions
- [ ] Collect and analyze feedback

## Story Points: 13
''',
            'labels': ['documentation', 'P1-high'],
            'milestone': 'Phase 5: Full Fleet Rollout',
        },
        {
            'title': '[Backend] Performance Optimization and Tuning',
            'body': '''## User Story
As a performance engineer, I want system optimized for 10k+ GPU scale.

## Description
Profile and optimize all components for production scale.

## Acceptance Criteria
- [ ] Database queries optimized (<100ms p95)
- [ ] API latency <200ms p95
- [ ] Stream processor handles 100k events/sec
- [ ] ML inference <100ms p95
- [ ] Memory usage optimized
- [ ] CPU utilization <70% average

## Technical Tasks
- [ ] Profile all components
- [ ] Optimize database queries and indexes
- [ ] Tune application performance
- [ ] Optimize ML inference
- [ ] Load test at 2x expected volume
- [ ] Document performance baselines

## Story Points: 13
''',
            'labels': ['enhancement', 'backend', 'P1-high'],
            'milestone': 'Phase 5: Full Fleet Rollout',
        },
        {
            'title': '[Backend] Disaster Recovery Testing',
            'body': '''## User Story
As a reliability engineer, I want DR procedures validated through testing.

## Description
Test all disaster recovery scenarios and validate recovery procedures.

## Acceptance Criteria
- [ ] Database failover tested
- [ ] Kafka cluster failover tested
- [ ] K8s node failure tested
- [ ] Data center outage simulated
- [ ] Recovery time < 15 minutes
- [ ] No data loss during failover

## Technical Tasks
- [ ] Create DR test scenarios
- [ ] Test database failover
- [ ] Test Kafka failover
- [ ] Simulate datacenter outage
- [ ] Measure recovery times
- [ ] Update DR runbooks
- [ ] Document test results

## Story Points: 8
''',
            'labels': ['feature', 'infrastructure', 'P1-high'],
            'milestone': 'Phase 5: Full Fleet Rollout',
        },
        {
            'title': '[Documentation] Production Operations Manual',
            'body': '''## User Story
As an operator, I want comprehensive operations manual for production system.

## Description
Complete ops manual covering deployment, monitoring, troubleshooting, DR.

## Acceptance Criteria
- [ ] Deployment procedures
- [ ] Monitoring and alerting guide
- [ ] Troubleshooting flowcharts
- [ ] DR procedures and runbooks
- [ ] Performance tuning guide
- [ ] Security hardening checklist

## Technical Tasks
- [ ] Document deployment procedures
- [ ] Write monitoring guide
- [ ] Create troubleshooting guides
- [ ] Document DR procedures
- [ ] Add performance tuning section
- [ ] Create security checklist

## Story Points: 8
''',
            'labels': ['documentation', 'P1-high'],
            'milestone': 'Phase 5: Full Fleet Rollout',
        },
        
        # ============================================================================
        # PHASE 6: CONTINUOUS IMPROVEMENT (Ongoing)
        # ============================================================================
        {
            'title': '[EPIC] Continuous Improvement Program',
            'body': '''## Epic Overview
Ongoing improvements to models, features, and system capabilities.

## Goals
- Model performance improves month-over-month
- New features based on operator feedback
- System reliability >99.99%
- Economic ROI >10x

## Components
- Weekly model retraining
- A/B testing framework
- Feature experimentation
- Performance monitoring
- Community feedback loop

## Success Criteria
- [ ] Models improving consistently
- [ ] User satisfaction >90%
- [ ] System uptime >99.99%
- [ ] ROI exceeds targets

## Related Issues
Long-term platform evolution.
''',
            'labels': ['epic', 'enhancement', 'P2-medium'],
            'milestone': 'Phase 6: Continuous Improvement',
        },
        {
            'title': '[ML] Implement A/B Testing Framework',
            'body': '''## User Story
As an ML engineer, I want to A/B test new models against production.

## Description
Build framework for safe deployment and testing of new ML models.

## Acceptance Criteria
- [ ] Traffic splitting between model versions
- [ ] Performance metrics tracked per version
- [ ] Statistical significance testing
- [ ] Automatic rollback on regression
- [ ] Gradual rollout support (10% → 50% → 100%)
- [ ] Dashboard showing A/B test results

## Technical Tasks
- [ ] Implement traffic splitting logic
- [ ] Add version tracking to predictions
- [ ] Calculate performance metrics per version
- [ ] Implement statistical tests
- [ ] Add automatic rollback
- [ ] Create A/B testing dashboard
- [ ] Document A/B testing process

## Story Points: 13
''',
            'labels': ['feature', 'ml', 'P2-medium'],
            'milestone': 'Phase 6: Continuous Improvement',
        },
        {
            'title': '[ML] Advanced Feature Engineering',
            'body': '''## User Story
As an ML engineer, I want to experiment with advanced features like NVLink metrics.

## Description
Expand feature set with NVLink, workload-specific, and interaction features.

## Acceptance Criteria
- [ ] NVLink bandwidth and error features
- [ ] Workload-specific features (HPC vs AI)
- [ ] Feature interactions (temp × ECC errors)
- [ ] Time-of-day patterns
- [ ] Seasonal adjustments
- [ ] A/B tested against baseline features

## Technical Tasks
- [ ] Collect NVLink metrics
- [ ] Extract workload characteristics
- [ ] Calculate feature interactions
- [ ] Add temporal features
- [ ] Train models with new features
- [ ] A/B test performance
- [ ] Document new features

## Story Points: 13
''',
            'labels': ['feature', 'ml', 'P3-low'],
            'milestone': 'Phase 6: Continuous Improvement',
        },
        {
            'title': '[ML] Root Cause Analysis Automation',
            'body': '''## User Story
As an operator, I want automated RCA when failures occur.

## Description
Build ML system to automatically diagnose failure root causes.

## Acceptance Criteria
- [ ] Analyzes failure symptoms
- [ ] Identifies most likely root cause
- [ ] Provides supporting evidence
- [ ] Suggests remediation steps
- [ ] Learns from operator feedback
- [ ] Accuracy >70%

## Technical Tasks
- [ ] Create failure symptom taxonomy
- [ ] Build classification model
- [ ] Implement evidence gathering
- [ ] Create remediation knowledge base
- [ ] Add feedback collection
- [ ] Train RCA model
- [ ] Validate with operators

## Story Points: 13
''',
            'labels': ['feature', 'ml', 'P3-low'],
            'milestone': 'Phase 6: Continuous Improvement',
        },
        {
            'title': '[Backend] Secondary Market Platform Integration',
            'body': '''## User Story
As a sales manager, I want automatic listing on secondary market platforms.

## Description
Integrate with GPU marketplaces for automated listing and pricing.

## Acceptance Criteria
- [ ] API integration with marketplace(s)
- [ ] Automatic listing creation
- [ ] Dynamic pricing updates
- [ ] Sale tracking and confirmation
- [ ] Inventory sync
- [ ] Commission calculations

## Technical Tasks
- [ ] Integrate marketplace APIs
- [ ] Implement listing automation
- [ ] Build pricing sync service
- [ ] Track sales and outcomes
- [ ] Sync inventory status
- [ ] Document integration

## Story Points: 13
''',
            'labels': ['feature', 'backend', 'P3-low'],
            'milestone': 'Phase 6: Continuous Improvement',
        },
        {
            'title': '[ML] Deep Learning Models for Anomaly Detection',
            'body': '''## User Story
As an ML engineer, I want to experiment with deep learning for anomaly detection.

## Description
Research and implement advanced deep learning models (Autoencoders, VAE).

## Acceptance Criteria
- [ ] Autoencoder trained on healthy GPU data
- [ ] Anomaly scores calculated
- [ ] Compared against Isolation Forest
- [ ] Performance benchmarked
- [ ] Documentation of findings
- [ ] Decision on production deployment

## Technical Tasks
- [ ] Research DL architectures
- [ ] Implement autoencoder in PyTorch
- [ ] Train on healthy data
- [ ] Evaluate anomaly detection
- [ ] Compare with existing methods
- [ ] Document results
- [ ] Present findings

## Story Points: 13
''',
            'labels': ['feature', 'ml', 'P3-low'],
            'milestone': 'Phase 6: Continuous Improvement',
        },
        {
            'title': '[Frontend] Mobile App for Fleet Management',
            'body': '''## User Story
As a manager, I want mobile app to monitor fleet health on the go.

## Description
Build iOS/Android app for monitoring GPU health and receiving alerts.

## Acceptance Criteria
- [ ] Real-time fleet health dashboard
- [ ] Push notifications for alerts
- [ ] GPU detail views
- [ ] Prediction summaries
- [ ] Economic recommendations
- [ ] Works on iOS and Android

## Technical Tasks
- [ ] Design mobile UI/UX
- [ ] Build React Native app
- [ ] Integrate with REST API
- [ ] Implement push notifications
- [ ] Add authentication
- [ ] Test on both platforms
- [ ] Publish to app stores

## Story Points: 21
''',
            'labels': ['feature', 'frontend', 'P3-low'],
            'milestone': 'Phase 6: Continuous Improvement',
        },
        {
            'title': '[Backend] Automated Workload Migration',
            'body': '''## User Story
As an orchestrator, I want workloads automatically migrated away from degraded GPUs.

## Description
Build system to automatically migrate jobs from at-risk GPUs.

## Acceptance Criteria
- [ ] Integration with workload scheduler (Kubernetes, Slurm)
- [ ] Automatic job migration when GPU degraded
- [ ] Graceful job handling (checkpoints)
- [ ] Operator notifications
- [ ] Configurable migration policies
- [ ] Success rate >95%

## Technical Tasks
- [ ] Integrate with scheduler API
- [ ] Implement migration logic
- [ ] Handle checkpointing
- [ ] Add notification system
- [ ] Configure migration policies
- [ ] Test migration scenarios
- [ ] Document integration

## Story Points: 21
''',
            'labels': ['feature', 'backend', 'P3-low'],
            'milestone': 'Phase 6: Continuous Improvement',
        },
        {
            'title': '[Backend] Advanced Economic Optimization',
            'body': '''## User Story
As a CFO, I want portfolio-level optimization for GPU lifecycle decisions.

## Description
Apply portfolio theory to optimize fleet-wide economic decisions.

## Acceptance Criteria
- [ ] Portfolio optimization model
- [ ] Risk-adjusted returns calculated
- [ ] Diversification strategies
- [ ] Budget constraints respected
- [ ] Multi-objective optimization
- [ ] Scenario analysis support

## Technical Tasks
- [ ] Research portfolio optimization
- [ ] Implement optimization algorithms
- [ ] Add risk calculations
- [ ] Build constraint handling
- [ ] Create scenario simulator
- [ ] Validate with historical data
- [ ] Document methodology

## Story Points: 21
''',
            'labels': ['feature', 'backend', 'P3-low'],
            'milestone': 'Phase 6: Continuous Improvement',
        },
        {
            'title': '[Documentation] Community Feedback Program',
            'body': '''## User Story
As a product owner, I want structured feedback from operators and users.

## Description
Establish feedback collection and feature prioritization process.

## Acceptance Criteria
- [ ] Feedback collection mechanism
- [ ] Monthly user surveys
- [ ] Feature request tracking
- [ ] Public roadmap
- [ ] Community voting on features
- [ ] Regular release notes

## Technical Tasks
- [ ] Set up feedback forms
- [ ] Create feature request tracker
- [ ] Build public roadmap
- [ ] Implement voting system
- [ ] Schedule monthly surveys
- [ ] Create release note template
- [ ] Document feedback process

## Story Points: 5
''',
            'labels': ['documentation', 'enhancement', 'P2-medium'],
            'milestone': 'Phase 6: Continuous Improvement',
        },
    ]
    
    print("\nCreating issues...")
    created_issues = []
    
    for i, issue in enumerate(issues, 1):
        try:
            # Get milestone number if specified
            milestone_number = None
            if issue.get('milestone') and issue['milestone'] in milestone_numbers:
                milestone_number = milestone_numbers[issue['milestone']]
            
            payload = {
                'title': issue['title'],
                'body': issue['body'],
                'labels': issue['labels']
            }
            
            if milestone_number:
                payload['milestone'] = milestone_number
            
            response = requests.post(
                f'{API_BASE}/issues',
                headers=headers,
                json=payload
            )
            
            if response.status_code == 201:
                data = response.json()
                created_issues.append(data)
                print(f"✓ [{i}/{len(issues)}] Created issue #{data['number']}: {issue['title']}")
            else:
                print(f"✗ [{i}/{len(issues)}] Failed to create: {issue['title']} - {response.status_code}")
                if response.status_code == 403:
                    print("   Rate limited or permission denied. Waiting 60 seconds...")
                    import time
                    time.sleep(60)
        
        except Exception as e:
            print(f"✗ [{i}/{len(issues)}] Error creating {issue['title']}: {e}")
    
    return created_issues

def main():
    """Main execution"""
    if not GITHUB_TOKEN:
        print("❌ Error: GITHUB_TOKEN environment variable not set")
        print("Export your token: export GITHUB_TOKEN='your_token_here'")
        return
    
    print("=" * 70)
    print("GPU Health Monitor - GitHub Project Setup")
    print("=" * 70)
    
    # Create labels
    create_labels()
    
    # Create milestones
    milestone_numbers = create_milestones()
    
    # Create issues
    created_issues = create_issues(milestone_numbers)
    
    print("\n" + "=" * 70)
    print("✅ Project setup complete!")
    print("=" * 70)
    print(f"\nCreated:")
    print(f"  - {len(milestone_numbers)} milestones")
    print(f"  - {len(created_issues)} issues")
    print(f"\nView your project at:")
    print(f"  https://github.com/{REPO_OWNER}/{REPO_NAME}/issues")
    print(f"  https://github.com/{REPO_OWNER}/{REPO_NAME}/milestones")
    print("\nNext steps:")
    print("  1. Create a GitHub Project board")
    print("  2. Link issues to the project")
    print("  3. Organize columns: Backlog, To Do, In Progress, Review, Done")

if __name__ == '__main__':
    main()
