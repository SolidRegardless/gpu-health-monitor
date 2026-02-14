# GPU Health Monitor - Technology Deep Dive

> **A Beginner's Guide to Every Technology in the Stack**
>
> This document explains every software component, library, framework, and tool used in the GPU Health Monitor system, with special focus on monitoring NVIDIA A100 and H100 GPUs in production environments.

---

## Table of Contents

1. [Infrastructure & Orchestration](#1-infrastructure--orchestration)
2. [Message Streaming Platform](#2-message-streaming-platform)
3. [Time-Series Database](#3-time-series-database)
4. [Visualization & Management](#4-visualization--management)
5. [Machine Learning Stack](#5-machine-learning-stack)
6. [Application Framework](#6-application-framework)
7. [Python Libraries](#7-python-libraries)
8. [GPU Monitoring Foundation](#8-gpu-monitoring-foundation)
9. [Development & Deployment](#9-development--deployment)

---

## 1. Infrastructure & Orchestration

### Docker

**What it is:** A platform for packaging applications into isolated containers that run consistently anywhere.

**Why we use it:**
- **Consistency**: Our GPU monitoring stack has 17 different services. Docker ensures they all work together regardless of the host OS.
- **Isolation**: Each service (Kafka, TimescaleDB, Grafana, ML models) runs in its own container with its own dependencies.
- **Reproducibility**: The exact same environment runs on your laptop, a test server, or Azure production.

**How we use it in GPU monitoring:**
```
Mock DCGM → Container 1 (simulates NVIDIA GPUs)
Collector → Container 2 (scrapes GPU metrics)
Kafka → Container 3 (streams metrics)
TimescaleDB → Container 4 (stores time-series data)
ML Predictor → Container 5 (predicts failures)
... (17 containers total)
```

**Key Features We Use:**
- **Multi-container apps**: Our system needs many services working together
- **Volume mounting**: Persist database data and configuration files
- **Networking**: Containers communicate via internal network (gpu-monitor-net)
- **Health checks**: Automatically restart failed containers

**Docker for GPUs:**
- NVIDIA provides `nvidia-docker` for GPU passthrough to containers
- In production, you'd use `--gpus all` to give containers access to physical GPUs
- We simulate GPUs, but the architecture supports real DCGM with minimal changes

---

### Docker Compose

**What it is:** A tool for defining and running multi-container Docker applications using a YAML file.

**Why we use it:**
- **Simplified deployment**: Single command (`docker-compose up`) starts all 17 services
- **Dependency management**: Automatically starts services in the right order (Zookeeper → Kafka → Processors)
- **Configuration as code**: Our entire stack is defined in `docker-compose.yml`

**How it works for GPU monitoring:**
```yaml
services:
  # GPU metrics source
  mock-dcgm:
    build: ../src/mock-dcgm
    ports: ["9400:9400"]
  
  # Metrics collector
  collector:
    depends_on: [mock-dcgm, kafka]
    environment:
      DCGM_ENDPOINT: "http://mock-dcgm:9400/metrics"
  
  # Stream processing
  kafka:
    depends_on: [zookeeper]
  
  # (... 14 more services)
```

**Key Features We Use:**
- **Service dependencies**: `depends_on` ensures Kafka starts before collectors
- **Environment variables**: Configure endpoints, intervals, database credentials
- **Named networks**: All services communicate via `gpu-monitor-net`
- **Volume mounts**: Share configuration files and persist data

**Production GPU Monitoring:**
In a real datacenter:
1. Replace `mock-dcgm` with real NVIDIA DCGM exporter
2. Deploy multiple collectors (one per GPU node)
3. Scale Kafka brokers for higher throughput
4. Use external TimescaleDB cluster for HA

---

### Terraform

**What it is:** Infrastructure as Code (IaC) tool that lets you define cloud resources in configuration files.

**Why we use it:**
- **Version control**: Infrastructure changes are tracked in Git
- **Reproducibility**: Destroy and rebuild entire environments in minutes
- **Documentation**: The `.tf` files are living documentation of your Azure setup
- **Safety**: `terraform plan` shows exactly what will change before applying

**How we use it for GPU monitoring:**
```hcl
# Creates Azure VM for GPU monitoring demo
resource "azurerm_linux_virtual_machine" "gpu_monitor" {
  name     = "gpu-health-monitor-vm"
  size     = "Standard_DC1ds_v3"  # 1 vCPU, 8GB RAM
  location = "eastus"
  
  # Installs Docker via cloud-init
  custom_data = base64encode(file("cloud-init.yaml"))
}
```

**Key Features We Use:**
- **Resource dependencies**: Terraform creates VNet → Subnet → NIC → VM in correct order
- **State management**: Tracks what exists in Azure vs what's defined in code
- **Outputs**: Automatically captures VM IP address for SSH/Grafana access
- **Idempotent**: Re-running `terraform apply` only changes what's different

**For GPU Monitoring at Scale:**
- Define GPU node pools with NVIDIA drivers pre-installed
- Configure accelerated networking for high-throughput metrics
- Set up auto-scaling based on GPU utilization
- Create multi-region deployments for global GPU fleets

---

## 2. Message Streaming Platform

### Apache Kafka

**What it is:** A distributed event streaming platform that handles real-time data feeds at massive scale.

**Why we use it:**
- **Decoupling**: GPU metric collectors don't need to know about every consumer (validators, databases, ML models)
- **Scalability**: Can handle millions of GPU metrics per second across thousands of GPUs
- **Fault tolerance**: If TimescaleDB goes down, Kafka buffers metrics until it recovers
- **Replay capability**: Can reprocess historical metrics for new ML models

**How it works in GPU monitoring:**
```
[10 GPUs generating metrics every 10 seconds]
         ↓
    [Collector] → Kafka Topic: "gpu-metrics-raw"
         ↓
    [Validator] → Kafka Topic: "gpu-metrics-validated"
         ↓
    [Enricher] → Kafka Topic: "gpu-metrics-enriched"
         ↓
   [TimescaleDB Sink] → Permanent storage
```

**Key Concepts for GPU Monitoring:**

**Topics** (like folders for different data types):
- `gpu-metrics-raw`: Unvalidated metrics from DCGM
- `gpu-metrics-validated`: Cleaned, validated metrics
- `gpu-metrics-enriched`: With datacenter info, rack location, etc.

**Partitions** (parallel processing):
- Topic split into 3 partitions = 3 consumers can process in parallel
- Partition by `gpu_uuid` = all metrics for a GPU go to same partition (preserves order)

**Consumer Groups** (load balancing):
- Multiple validators read from `gpu-metrics-raw` in parallel
- If one fails, others take over its partitions

**Retention** (how long to keep data):
- Default: 7 days (for reprocessing, debugging)
- After 7 days, metrics only exist in TimescaleDB

**For High-End GPU Monitoring (A100/H100):**
- **High-frequency metrics**: A100s generate 100+ metrics every second
- **Burst tolerance**: Training job failures spike error metrics
- **Low latency**: Detect thermal throttling within 1 second
- **Guaranteed order**: Temperature readings must arrive in sequence

**Example Use Case:**
```
10,000 H100 GPUs × 100 metrics/sec = 1 million messages/sec
Kafka easily handles this with 3-5 broker nodes
```

---

### Apache Zookeeper

**What it is:** A coordination service that manages distributed systems (Kafka's "brain").

**Why Kafka needs it:**
- **Cluster coordination**: Tracks which Kafka brokers are alive
- **Leader election**: If a broker fails, Zookeeper picks a new leader
- **Configuration management**: Stores topic metadata, partitions, replicas
- **Consensus**: Ensures all brokers agree on cluster state

**How it works in our system:**
```
Zookeeper (port 2181)
    ↓
Manages Kafka cluster state
    ↓
Kafka (port 9092) knows:
- Which topics exist
- Where partitions are stored
- Which broker is leader for each partition
```

**For GPU Monitoring:**
- **Auto-failover**: If Kafka broker crashes, Zookeeper promotes replica
- **No single point of failure**: Multi-node Zookeeper prevents data loss
- **Service discovery**: Collectors find Kafka brokers via Zookeeper

**Production Setup:**
```
3 Zookeeper nodes (odd number for quorum)
5 Kafka brokers (distributed across availability zones)
= Survives 1 Zookeeper failure + 2 Kafka failures
```

---

## 3. Time-Series Database

### TimescaleDB

**What it is:** A PostgreSQL extension optimized for time-series data (metrics over time).

**Why we use it instead of regular PostgreSQL:**
- **Compression**: 10,000 GPUs × 100 metrics/sec × 30 days = 2.6 billion rows
  - Regular PostgreSQL: ~500 GB
  - TimescaleDB: ~50 GB (10x compression)
- **Fast queries**: "Show GPU temps for last hour" is 100x faster
- **Automatic partitioning**: Splits data into chunks by time (daily/weekly)
- **Continuous aggregates**: Pre-computed averages/max/min for dashboards

**How it stores GPU metrics:**
```sql
-- Traditional table (slow for billions of rows)
CREATE TABLE gpu_metrics (
    time TIMESTAMP,
    gpu_uuid TEXT,
    temperature REAL,
    power REAL
    -- ... 27 more columns
);

-- TimescaleDB hypertable (optimized)
SELECT create_hypertable('gpu_metrics', 'time');

-- Automatically splits into chunks:
_timescaledb_internal._hyper_1_1_chunk  -- Jan 1-7
_timescaledb_internal._hyper_1_2_chunk  -- Jan 8-14
_timescaledb_internal._hyper_1_3_chunk  -- Jan 15-21
```

**Key Features for GPU Monitoring:**

**1. Hypertables** (partitioned by time):
```sql
-- Insert 1 million rows/second
INSERT INTO gpu_metrics VALUES (...);  -- Automatically routed to correct chunk

-- Query last hour (only scans recent chunks)
SELECT * FROM gpu_metrics 
WHERE time > NOW() - INTERVAL '1 hour';  -- Fast!
```

**2. Compression** (saves 90% storage):
```sql
-- Compress data older than 7 days
ALTER TABLE gpu_metrics SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'gpu_uuid'
);

SELECT add_compression_policy('gpu_metrics', INTERVAL '7 days');
```

**3. Continuous Aggregates** (pre-computed dashboards):
```sql
-- Real-time dashboard query (slow):
SELECT gpu_uuid, AVG(temperature) 
FROM gpu_metrics 
WHERE time > NOW() - INTERVAL '24 hours'
GROUP BY gpu_uuid, time_bucket('1 hour', time);  -- Scans millions of rows

-- Continuous aggregate (instant):
CREATE MATERIALIZED VIEW gpu_hourly_stats
WITH (timescaledb.continuous) AS
SELECT 
  time_bucket('1 hour', time) AS hour,
  gpu_uuid,
  AVG(temperature) AS avg_temp,
  MAX(power_usage) AS max_power
FROM gpu_metrics
GROUP BY hour, gpu_uuid;

-- Dashboard query (fast):
SELECT * FROM gpu_hourly_stats WHERE hour > NOW() - INTERVAL '24 hours';
```

**4. Retention Policies** (auto-delete old data):
```sql
-- Keep raw metrics for 30 days, then drop
SELECT add_retention_policy('gpu_metrics', INTERVAL '30 days');

-- Keep hourly aggregates for 1 year
SELECT add_retention_policy('gpu_hourly_stats', INTERVAL '365 days');
```

**For A100/H100 GPU Monitoring:**

**Typical metrics per GPU:**
- 30 core metrics (temperature, power, utilization, etc.)
- 12 NVLink bandwidth metrics (GPU-to-GPU communication)
- 6 memory metrics (used, free, ECC errors)
- 10 performance metrics (SM activity, tensor core usage)
= **58 values per GPU** every 10 seconds

**Scale example:**
```
1,000 H100 GPUs × 58 metrics × 6 samples/min × 60 min × 24 hours
= 501 million metric points per day
= 15 billion points per month

TimescaleDB handles this on a single server with:
- 32 GB RAM
- 1 TB SSD
- ~2 ms query latency for "last hour" queries
```

**Specialized Queries We Use:**

**1. Find GPUs with thermal throttling:**
```sql
SELECT gpu_uuid, COUNT(*) as throttle_events
FROM gpu_metrics
WHERE time > NOW() - INTERVAL '1 hour'
  AND throttle_reasons > 0
GROUP BY gpu_uuid
ORDER BY throttle_events DESC;
```

**2. Detect memory ECC error spikes:**
```sql
SELECT gpu_uuid, time, ecc_dbe_volatile
FROM gpu_metrics
WHERE time > NOW() - INTERVAL '1 day'
  AND ecc_dbe_volatile > 0  -- Double-bit errors (critical)
ORDER BY time DESC;
```

**3. Power consumption trends:**
```sql
SELECT 
  time_bucket('1 hour', time) AS hour,
  SUM(power_usage) / 1000.0 AS total_kw
FROM gpu_metrics
WHERE time > NOW() - INTERVAL '7 days'
GROUP BY hour
ORDER BY hour;
```

---

### PostgreSQL (the base of TimescaleDB)

**What it is:** The world's most advanced open-source relational database.

**Why TimescaleDB built on top of it:**
- **ACID compliance**: GPU failure predictions must be reliable (no lost data)
- **SQL compatibility**: Use standard SQL queries, tools (Grafana, psql, Adminer)
- **JSON support**: Store complex data (GPU tags, configuration as JSONB)
- **Triggers**: Auto-update `updated_at` timestamps
- **Views**: Create virtual tables for complex queries

**Features we use for GPU metadata:**

**1. Asset Management:**
```sql
CREATE TABLE gpu_assets (
  gpu_uuid TEXT PRIMARY KEY,
  model TEXT NOT NULL,  -- 'NVIDIA H100-SXM5-80GB'
  architecture TEXT,    -- 'Hopper'
  memory_gb INTEGER,    -- 80
  datacenter TEXT,
  rack_id TEXT,
  purchase_date DATE,
  warranty_expiry DATE,
  tags JSONB            -- Flexible metadata
);

-- Find all H100s purchased in last 6 months
SELECT * FROM gpu_assets
WHERE model LIKE '%H100%'
  AND purchase_date > CURRENT_DATE - INTERVAL '6 months';
```

**2. JSONB for flexible metadata:**
```sql
-- Store GPU-specific settings
UPDATE gpu_assets 
SET tags = '{"profile": "ML_training", "max_power": 400, "fan_curve": "aggressive"}'::jsonb
WHERE gpu_uuid = 'GPU-uk1aaa111bbb';

-- Query by JSON field
SELECT gpu_uuid, tags->>'profile' AS profile
FROM gpu_assets
WHERE tags->>'profile' = 'ML_training';
```

**3. Triggers for automatic timestamps:**
```sql
CREATE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_gpu_assets_updated_at
BEFORE UPDATE ON gpu_assets
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
```

---

## 4. Visualization & Management

### Grafana

**What it is:** A multi-platform analytics and visualization tool that creates beautiful, interactive dashboards from time-series data.

**Why we use it for GPU monitoring:**
- **Real-time visualization**: See GPU temperatures update every second
- **Multi-datasource**: Connects to TimescaleDB, Prometheus, InfluxDB, etc.
- **Alerting**: Notify when GPU temps exceed thresholds
- **Dashboard sharing**: Standardize monitoring across datacenter teams
- **Template variables**: Single dashboard for 10,000 GPUs (select via dropdown)

**How we use it:**

**6 dashboards covering different views:**

1. **Fleet Overview** - All GPUs at once
   - 10 temperature lines on one graph
   - Total power consumption
   - Error count heatmap

2. **Datacenter Overview** - Aggregate by datacenter
   - DC-EAST-01: 5 GPUs, avg 68°C, 1.5kW total
   - UK-SOUTH-01: 5 GPUs, avg 71°C, 1.6kW total

3. **GPU Detail** - Single GPU deep dive
   - Temperature over time (4-hour window)
   - Power usage patterns
   - ECC error history
   - Throttle event timeline

4. **Predictive Analytics** - ML failure predictions
   - 7/30/90-day failure probability
   - Confidence scores
   - Time-to-failure estimates

5. **Health Trends** - Long-term patterns
   - Temperature drift over weeks
   - Power efficiency degradation
   - Memory error accumulation

6. **Simple Overview** - Executive summary
   - Active GPU count
   - Avg fleet temperature
   - Critical alerts

**Key Grafana Features for GPU Monitoring:**

**1. Template Variables** (dynamic dashboards):
```sql
-- Variable: gpu_uuid (dropdown selector)
SELECT DISTINCT gpu_uuid FROM gpu_assets ORDER BY gpu_uuid;

-- Panel query uses variable:
SELECT time, gpu_temp 
FROM gpu_metrics 
WHERE gpu_uuid = '$gpu_uuid'  -- $gpu_uuid filled by dropdown
  AND time > NOW() - INTERVAL '4 hours';
```

**2. Transformations** (reshape data):
- **Pivot**: Turn rows into columns for multi-GPU comparison
- **Join**: Combine metrics with asset metadata
- **Calculate**: Derive power efficiency (utilization / power)

**3. Panel Types for GPU Metrics:**
- **Time Series**: Temperature/power trends over time
- **Gauge**: Current temperature with min/max scale (0-100°C)
- **Stat**: Single value (Current Power: 312W)
- **Table**: List of GPUs with current stats
- **Heatmap**: Error patterns across GPU fleet

**4. Alerting** (coming soon to our setup):
```yaml
# Alert if GPU temp > 85°C for 5 minutes
Alert: GPU High Temperature
Condition: WHEN avg() OF query(A, 5m) > 85
Notify: PagerDuty, Slack, Email
```

**Example Dashboard Panel - GPU Temperature:**
```sql
SELECT 
  time_bucket('10 seconds', time) AS time,
  gpu_uuid,
  AVG(gpu_temp) AS temperature
FROM gpu_metrics
WHERE time > NOW() - INTERVAL '4 hours'
  AND gpu_uuid = '$gpu_uuid'
GROUP BY time, gpu_uuid
ORDER BY time;
```
Displays as: Line graph, auto-refreshing every 10 seconds, zooms/pans with mouse

**For Large GPU Fleets:**
- **Query caching**: Pre-compute aggregates for fast dashboard load
- **Downsampling**: Show 1-minute averages for 30-day view (not every 10-second sample)
- **Alert folders**: Organize by datacenter, team, severity
- **RBAC**: ML team sees training GPUs, DevOps sees infrastructure GPUs

---

### Adminer

**What it is:** A lightweight database management tool (like phpMyAdmin but better).

**Why we use it:**
- **Quick database access**: Browse tables, run SQL queries via web UI
- **No installation**: Single PHP file (but we use Docker container)
- **Multi-database**: Works with PostgreSQL, MySQL, SQLite, etc.
- **Debugging**: Inspect raw metrics, verify data pipeline

**How we use it for GPU monitoring:**
```
http://localhost:8080
Login:
  System: PostgreSQL
  Server: timescaledb
  Username: gpu_monitor
  Password: (from docker-compose.yml)

Then:
- Browse gpu_metrics table (see raw sensor data)
- Check gpu_assets (verify GPU inventory)
- Run ad-hoc queries (find anomalies)
- Export data as CSV (for offline analysis)
```

**Typical debugging tasks:**

**1. Verify metrics are flowing:**
```sql
SELECT gpu_uuid, COUNT(*), MAX(time) as latest
FROM gpu_metrics
GROUP BY gpu_uuid;

-- Should show 10 GPUs with recent timestamps
```

**2. Check for data gaps:**
```sql
SELECT 
  gpu_uuid,
  time,
  LEAD(time) OVER (PARTITION BY gpu_uuid ORDER BY time) - time AS gap
FROM gpu_metrics
WHERE time > NOW() - INTERVAL '1 hour'
ORDER BY gap DESC NULLS LAST
LIMIT 10;

-- Gaps > 10 seconds indicate collector issues
```

**3. Inspect ML predictions:**
```sql
SELECT 
  gpu_uuid,
  prediction_time,
  failure_probability_7d,
  failure_probability_30d,
  predicted_failure_type
FROM gpu_failure_predictions
ORDER BY failure_probability_30d DESC;
```

**Production Note:** 
Adminer is for development/debugging only. In production:
- Disable or restrict to VPN-only access
- Use read-only credentials
- Enable audit logging

---

## 5. Machine Learning Stack

### XGBoost

**What it is:** eXtreme Gradient Boosting - a highly efficient implementation of gradient boosting for regression and classification.

**Why we use it for GPU failure prediction:**
- **Accuracy**: Best-in-class for tabular data (our 27 GPU features)
- **Speed**: Trains on millions of samples in seconds
- **Handles missing data**: Some GPUs might not report all metrics
- **Feature importance**: Shows which metrics predict failures (temperature? ECC errors?)
- **Probabilistic predictions**: Outputs 0-100% failure probability

**How it works (simplified):**

**Traditional model** (too simple):
```
IF temperature > 85°C THEN failure_risk = high
```

**XGBoost** (ensemble of decision trees):
```
Tree 1: IF temp > 75 AND ecc_errors > 5 THEN +0.2 risk
Tree 2: IF power > 350 AND age > 24mo THEN +0.15 risk
Tree 3: IF mem_temp > 95 THEN +0.3 risk
... (100-500 trees)

Final prediction = sum of all tree outputs
= 0.65 (65% failure probability in next 30 days)
```

**How we use it in GPU monitoring:**

**Training phase:**
```python
import xgboost as xgb

# Features: 27 metrics per GPU
features = [
    'avg_temp_7d', 'max_temp_7d', 'temp_stddev',
    'avg_power_7d', 'max_power_7d',
    'ecc_sbe_rate', 'ecc_dbe_total',
    'throttle_event_count',
    'gpu_age_months',
    # ... 18 more
]

# Labels: did GPU fail in next 30 days?
labels = [0, 0, 1, 0, 0, 1, ...]  # 1 = failed, 0 = healthy

# Train model
model = xgb.XGBClassifier(
    n_estimators=200,       # 200 decision trees
    max_depth=6,             # Tree depth (prevents overfitting)
    learning_rate=0.1,       # How fast to learn
    objective='binary:logistic'  # Predict probability
)

model.fit(features, labels)

# Save for production
model.save_model('/models/gpu_failure_predictor.json')
```

**Prediction phase (every 5 minutes):**
```python
# Extract features from recent metrics
current_features = extract_features(gpu_uuid='GPU-uk5eee555fff')
# [71.2, 95.3, 4.8, 330.5, 415.2, 0.015, 12, 45, 28, ...]

# Predict failure probability
prediction = model.predict_proba(current_features)[0][1]
# 0.118 = 11.8% chance of failure in next 30 days

# Store in database
INSERT INTO gpu_failure_predictions VALUES (
  gpu_uuid, NOW(), 0.05, 0.118, 0.245, 'thermal', 0.75
);
```

**Feature importance (what matters most):**
```python
xgb.plot_importance(model)

# Output:
# ecc_dbe_total: 0.35        ← Double-bit errors = critical
# max_temp_7d: 0.22          ← Peak temperatures
# gpu_age_months: 0.15       ← Older GPUs fail more
# throttle_event_count: 0.12 ← Throttling = stress
# avg_power_7d: 0.08         ← Power consumption
```

**For A100/H100 Failure Prediction:**

**Common failure modes:**
1. **Thermal failures** (40% of failures)
   - Predictor: `max_temp_7d > 85`, `temp_variance > 5`
   - Early warning: 2-3 weeks before failure

2. **Memory failures** (30% of failures)
   - Predictor: `ecc_dbe_total > 5`, `ecc_sbe_rate increasing`
   - Early warning: 1-2 weeks before failure

3. **Power supply failures** (20% of failures)
   - Predictor: `power_variance > 50W`, `throttle_events > 10/day`
   - Early warning: 3-4 weeks before failure

4. **Aging/wear-out** (10% of failures)
   - Predictor: `gpu_age_months > 36`, `degradation_factor < 0.85`
   - Gradual decline, replaceable during maintenance

**Model Performance:**
- **Precision**: 75% (of predicted failures, 75% actually fail)
- **Recall**: 60% (catches 60% of all failures before they happen)
- **False alarm rate**: 25% (acceptable for proactive maintenance)

---

### MLflow

**What it is:** An open-source platform for managing the ML lifecycle (training, tracking, deployment).

**Why we use it:**
- **Experiment tracking**: Compare 50 different XGBoost configurations
- **Model versioning**: Track which model version is in production
- **Reproducibility**: Re-train model with exact same parameters
- **Model registry**: Central storage for all GPU failure models

**How we use it:**

**1. Track experiments:**
```python
import mlflow

with mlflow.start_run(run_name='xgboost_v2_higher_depth'):
    # Log parameters
    mlflow.log_param('n_estimators', 200)
    mlflow.log_param('max_depth', 8)  # Increased from 6
    
    # Train model
    model = xgb.XGBClassifier(n_estimators=200, max_depth=8)
    model.fit(X_train, y_train)
    
    # Evaluate
    accuracy = model.score(X_test, y_test)
    mlflow.log_metric('accuracy', accuracy)  # 0.847
    mlflow.log_metric('precision', 0.75)
    mlflow.log_metric('recall', 0.68)
    
    # Save model
    mlflow.xgboost.log_model(model, 'model')

# MLflow UI shows:
# Run 1: depth=6, accuracy=0.832
# Run 2: depth=8, accuracy=0.847 ← Better!
```

**2. Model registry:**
```python
# Register best model
mlflow.register_model(
    'runs:/abc123/model',
    'gpu-failure-predictor'
)

# Promote to production
client.transition_model_version_stage(
    name='gpu-failure-predictor',
    version=3,
    stage='Production'
)

# Load in production
model = mlflow.pyfunc.load_model(
    'models:/gpu-failure-predictor/Production'
)
```

**3. Compare experiments (MLflow UI):**
```
http://localhost:5000

Experiments view:
┌──────────────┬────────────┬──────────┬───────────┬────────┐
│ Run Name     │ max_depth  │ accuracy │ precision │ recall │
├──────────────┼────────────┼──────────┼───────────┼────────┤
│ xgb_v1       │ 4          │ 0.801    │ 0.68      │ 0.55   │
│ xgb_v2       │ 6          │ 0.832    │ 0.73      │ 0.62   │
│ xgb_v3       │ 8          │ 0.847    │ 0.75      │ 0.68   │ ← Best
│ randomforest │ 10         │ 0.812    │ 0.70      │ 0.60   │
└──────────────┴────────────┴──────────┴───────────┴────────┘
```

**For Production GPU Monitoring:**
- **A/B testing**: Run two models in parallel, compare predictions
- **Model drift detection**: Track accuracy over time (new GPU models might need retraining)
- **Automated retraining**: Trigger new training run when accuracy drops below 80%

---

### Scikit-learn

**What it is:** The most popular Python library for classical machine learning.

**Why we use it alongside XGBoost:**
- **Data preprocessing**: Scale features, handle missing values
- **Model evaluation**: Calculate precision, recall, F1-score
- **Feature selection**: Find most important metrics
- **Cross-validation**: Ensure model generalizes to new GPUs

**How we use it:**

**1. Feature scaling:**
```python
from sklearn.preprocessing import StandardScaler

# GPU metrics have different scales:
# temperature: 30-100°C
# power: 50-700W
# ecc_errors: 0-10,000

scaler = StandardScaler()
features_scaled = scaler.fit_transform(features)

# Now all features have mean=0, stddev=1
# XGBoost trains faster and more accurately
```

**2. Train/test split:**
```python
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    features, labels,
    test_size=0.2,      # 20% for testing
    stratify=labels,    # Keep same failure rate in both sets
    random_state=42     # Reproducible splits
)
```

**3. Model evaluation:**
```python
from sklearn.metrics import classification_report, confusion_matrix

predictions = model.predict(X_test)

print(classification_report(y_test, predictions))

# Output:
#               precision  recall  f1-score  support
# No failure      0.95      0.88     0.91      800
# Failure         0.75      0.68     0.71      200
# 
# accuracy                           0.84     1000
```

**4. Cross-validation:**
```python
from sklearn.model_selection import cross_val_score

# Test on 5 different train/test splits
scores = cross_val_score(model, features, labels, cv=5)
print(f"Accuracy: {scores.mean():.3f} (+/- {scores.std():.3f})")
# Accuracy: 0.842 (+/- 0.023)  ← Consistent across splits
```

---

### Pandas

**What it is:** Python library for data manipulation and analysis (think Excel but programmatic).

**Why we use it:**
- **Feature engineering**: Calculate rolling averages, trends from raw metrics
- **Data cleaning**: Handle missing values, outliers
- **Time-series operations**: Resample to different intervals
- **SQL-like operations**: Group, filter, aggregate GPU metrics

**How we use it for GPU monitoring:**

**1. Load metrics from database:**
```python
import pandas as pd
import psycopg2

conn = psycopg2.connect('dbname=gpu_health user=gpu_monitor')

df = pd.read_sql("""
    SELECT time, gpu_uuid, gpu_temp, power_usage, ecc_sbe_volatile
    FROM gpu_metrics
    WHERE time > NOW() - INTERVAL '7 days'
""", conn)

# Creates DataFrame:
#                    time          gpu_uuid  gpu_temp  power_usage  ecc_sbe_volatile
# 0  2026-02-06 10:00:00  GPU-abc123def456      67.2        305.8                 0
# 1  2026-02-06 10:00:10  GPU-abc123def456      67.5        308.2                 1
# ... (1M rows)
```

**2. Feature engineering:**
```python
# Calculate 7-day rolling average temperature
df['avg_temp_7d'] = df.groupby('gpu_uuid')['gpu_temp'].transform(
    lambda x: x.rolling(window='7d').mean()
)

# Temperature variance (stability indicator)
df['temp_stddev'] = df.groupby('gpu_uuid')['gpu_temp'].transform(
    lambda x: x.rolling(window='24h').std()
)

# ECC error rate (errors per hour)
df['ecc_error_rate'] = df.groupby('gpu_uuid')['ecc_sbe_volatile'].transform(
    lambda x: x.rolling(window='1h').sum()
)

# Power efficiency (utilization per watt)
df['power_efficiency'] = df['gpu_utilization'] / df['power_usage']
```

**3. Aggregate by GPU:**
```python
# Get statistics per GPU for last 7 days
gpu_stats = df.groupby('gpu_uuid').agg({
    'gpu_temp': ['mean', 'max', 'std'],
    'power_usage': ['mean', 'max'],
    'ecc_sbe_volatile': 'sum'
}).reset_index()

#           gpu_uuid  temp_mean  temp_max  temp_std  power_mean  power_max  ecc_sum
# 0  GPU-abc123...       67.2      78.5      3.2       305.8      380.2      12
# 1  GPU-def456...       72.1      88.3      5.8       310.5      395.7      87
```

**4. Detect anomalies:**
```python
# Find GPUs with abnormal temperature spikes
anomalies = df[df['gpu_temp'] > df['gpu_temp'].quantile(0.99)]

# GPUs with increasing ECC errors (failure warning)
error_trends = df.groupby('gpu_uuid')['ecc_sbe_volatile'].apply(
    lambda x: x.diff().mean()  # Average change per sample
)
failing_gpus = error_trends[error_trends > 5].index.tolist()
```

**5. Resample to different intervals:**
```python
# Downsample from 10-second samples to 1-minute averages
df_1min = df.set_index('time').groupby('gpu_uuid').resample('1min').agg({
    'gpu_temp': 'mean',
    'power_usage': 'mean',
    'gpu_utilization': 'mean'
}).reset_index()
```

---

### NumPy

**What it is:** Numerical Python - the foundation for all scientific computing in Python.

**Why we use it:**
- **Fast array operations**: 100x faster than Python lists for math
- **Vectorization**: Apply operations to entire arrays at once
- **Linear algebra**: Matrix operations for ML models
- **Random number generation**: Simulate GPU sensor noise

**How we use it:**

**1. Mock DCGM GPU simulation:**
```python
import numpy as np

# Simulate 10 GPUs with normal distribution around base temps
base_temps = np.array([65, 72, 68, 70, 62, 67, 60, 69, 64, 71])
noise = np.random.normal(0, 1.5, size=10)  # Random fluctuations
current_temps = base_temps + noise

# [66.2, 73.5, 67.1, 71.8, 60.9, 68.3, 59.2, 70.1, 65.4, 72.2]
```

**2. Feature scaling:**
```python
# Normalize features to 0-1 range
features = np.array([[67, 305], [72, 310], [68, 340]])
min_vals = features.min(axis=0)   # [67, 305]
max_vals = features.max(axis=0)   # [72, 340]

normalized = (features - min_vals) / (max_vals - min_vals)
# [[0.0, 0.0], [1.0, 0.14], [0.2, 1.0]]
```

**3. Moving averages:**
```python
temps = np.array([67, 68, 70, 71, 69, 67, 66])
window = 3

# 3-sample moving average
moving_avg = np.convolve(temps, np.ones(window)/window, mode='valid')
# [68.33, 69.67, 70.0, 69.0, 67.33]
```

**4. Statistical operations:**
```python
gpu_temps = np.array([67.2, 68.1, 72.5, 88.3, 67.9, 69.2])

mean = np.mean(gpu_temps)      # 72.2
median = np.median(gpu_temps)  # 68.65
std = np.std(gpu_temps)        # 7.8
percentile_95 = np.percentile(gpu_temps, 95)  # 85.1

# Detect outliers (> 2 standard deviations)
outliers = gpu_temps[np.abs(gpu_temps - mean) > 2*std]  # [88.3]
```

---

### SciPy

**What it is:** Scientific Python - advanced mathematical algorithms (optimization, signal processing, statistics).

**Why we use it:**
- **Signal processing**: Filter noisy GPU sensor readings
- **Statistical tests**: Detect significant changes in metrics
- **Interpolation**: Fill gaps in missing metrics
- **Optimization**: Tune hyperparameters

**How we use it:**

**1. Smooth noisy temperature readings:**
```python
from scipy.signal import savgol_filter

# Raw temperature readings (with sensor noise)
temps_raw = [67.2, 67.5, 67.3, 67.8, 67.4, 67.9, 67.6]

# Apply Savitzky-Golay filter (smooths while preserving trends)
temps_smooth = savgol_filter(temps_raw, window_length=5, polyorder=2)
# [67.2, 67.36, 67.52, 67.64, 67.72, 67.78, 67.6]
```

**2. Detect trend changes:**
```python
from scipy.stats import linregress

# Temperature over 7 days (is it increasing?)
days = [1, 2, 3, 4, 5, 6, 7]
temps = [67, 68, 69, 71, 72, 74, 75]

slope, intercept, r_value, p_value, std_err = linregress(days, temps)
# slope = 1.36 (temperature rising 1.36°C per day - concerning!)
```

**3. Fill missing data:**
```python
from scipy.interpolate import interp1d

# Metrics with gaps (collector failed at 10:10, 10:20)
times = [10.0, 10.1, 10.3, 10.4]
temps = [67.2, 67.5, 68.1, 68.3]

# Interpolate missing values
f = interp1d(times, temps, kind='linear')
temps_filled = f([10.0, 10.1, 10.2, 10.3, 10.4])
# [67.2, 67.5, 67.8, 68.1, 68.3]
```

---

## 6. Application Framework

### FastAPI

**What it is:** Modern Python web framework for building high-performance REST APIs.

**Why we use it:**
- **Speed**: 2-3x faster than Flask (built on async Python)
- **Auto documentation**: Generates interactive API docs automatically
- **Type validation**: Uses Python type hints to validate requests
- **Async support**: Handle thousands of concurrent metric queries

**How we use it for GPU monitoring API:**

**1. Query current GPU status:**
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="GPU Health Monitor API")

class GPUStatus(BaseModel):
    gpu_uuid: str
    temperature: float
    power_usage: float
    utilization: float
    status: str  # 'healthy', 'warning', 'critical'

@app.get("/api/gpu/{gpu_uuid}/status", response_model=GPUStatus)
async def get_gpu_status(gpu_uuid: str):
    # Query database for latest metrics
    result = await db.fetch_one(
        "SELECT * FROM gpu_metrics WHERE gpu_uuid = $1 ORDER BY time DESC LIMIT 1",
        gpu_uuid
    )
    
    # Determine health status
    status = 'healthy'
    if result['temperature'] > 85:
        status = 'critical'
    elif result['temperature'] > 75:
        status = 'warning'
    
    return GPUStatus(
        gpu_uuid=result['gpu_uuid'],
        temperature=result['temperature'],
        power_usage=result['power_usage'],
        utilization=result['gpu_utilization'],
        status=status
    )

# Auto-generated docs at http://localhost:8000/docs
```

**2. Get failure predictions:**
```python
@app.get("/api/gpu/{gpu_uuid}/prediction")
async def get_prediction(gpu_uuid: str):
    pred = await db.fetch_one("""
        SELECT failure_probability_30d, predicted_failure_type, confidence
        FROM gpu_failure_predictions
        WHERE gpu_uuid = $1
        ORDER BY prediction_time DESC LIMIT 1
    """, gpu_uuid)
    
    return {
        'gpu_uuid': gpu_uuid,
        'failure_probability_30d': pred['failure_probability_30d'],
        'failure_type': pred['predicted_failure_type'],
        'confidence': pred['confidence']
    }
```

**3. List GPUs by datacenter:**
```python
@app.get("/api/datacenters/{datacenter}/gpus")
async def list_datacenter_gpus(datacenter: str):
    gpus = await db.fetch_all("""
        SELECT 
            a.gpu_uuid, a.model, a.rack_id,
            m.gpu_temp, m.power_usage, m.gpu_utilization
        FROM gpu_assets a
        JOIN LATERAL (
            SELECT gpu_temp, power_usage, gpu_utilization
            FROM gpu_metrics
            WHERE gpu_uuid = a.gpu_uuid
            ORDER BY time DESC LIMIT 1
        ) m ON true
        WHERE a.datacenter = $1
    """, datacenter)
    
    return {'datacenter': datacenter, 'gpus': gpus, 'count': len(gpus)}

# GET /api/datacenters/UK-SOUTH-01/gpus
# Returns all 5 GPUs with current metrics
```

**Interactive API docs (automatic):**
```
http://localhost:8000/docs

Swagger UI:
- Browse all endpoints
- Test API calls directly in browser
- See request/response schemas
- Copy curl commands
```

---

### Flask

**What it is:** Lightweight Python web framework (used for mock DCGM exporter).

**Why we use it:**
- **Simplicity**: Perfect for simple HTTP endpoints
- **Minimal overhead**: Just serve Prometheus metrics, nothing fancy
- **Well-tested**: Industry standard since 2010

**How we use it:**

**Mock DCGM Prometheus exporter:**
```python
from flask import Flask, Response

app = Flask(__name__)

@app.route('/metrics')
def metrics():
    # Generate Prometheus-format metrics
    metrics_text = generate_prometheus_metrics()
    return Response(metrics_text, mimetype='text/plain')

@app.route('/health')
def health():
    return {
        'status': 'healthy',
        'gpu_count': 10,
        'uptime_seconds': get_uptime()
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9400)
```

**Prometheus metrics output:**
```
DCGM_FI_DEV_GPU_TEMP{gpu="0",UUID="GPU-abc123def456"} 67.2 1707844800000
DCGM_FI_DEV_POWER_USAGE{gpu="0",UUID="GPU-abc123def456"} 305.8 1707844800000
DCGM_FI_DEV_GPU_UTIL{gpu="0",UUID="GPU-abc123def456"} 85.3 1707844800000
...
```

---

### Uvicorn

**What it is:** Lightning-fast ASGI server for running FastAPI applications.

**Why we use it:**
- **Async support**: Handles thousands of concurrent API requests
- **HTTP/2**: Faster protocol for modern apps
- **WebSocket support**: Real-time GPU metric streaming (future feature)
- **Auto-reload**: Restarts on code changes during development

**How we run it:**
```python
# In production container
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# 4 workers = can handle 4000+ requests/second
```

---

## 7. Python Libraries

### kafka-python

**What it is:** Pure Python client for Apache Kafka.

**How we use it:**

**Producer (collector → Kafka):**
```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['kafka:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Send GPU metrics to Kafka
metric = {
    'gpu_uuid': 'GPU-abc123def456',
    'timestamp': 1707844800,
    'temperature': 67.2,
    'power': 305.8
}

producer.send('gpu-metrics-raw', value=metric)
producer.flush()  # Ensure sent
```

**Consumer (validator reads from Kafka):**
```python
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'gpu-metrics-raw',
    bootstrap_servers=['kafka:9092'],
    group_id='validators',
    auto_offset_reset='latest',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

for message in consumer:
    metric = message.value
    if validate(metric):
        # Forward to next topic
        producer.send('gpu-metrics-validated', value=metric)
```

---

### psycopg2-binary

**What it is:** PostgreSQL adapter for Python (connects to TimescaleDB).

**How we use it:**

**Insert metrics:**
```python
import psycopg2

conn = psycopg2.connect(
    'host=timescaledb dbname=gpu_health user=gpu_monitor password=***'
)
cur = conn.cursor()

cur.execute("""
    INSERT INTO gpu_metrics (
        time, gpu_uuid, gpu_temp, power_usage, gpu_utilization
    ) VALUES (%s, %s, %s, %s, %s)
""", (timestamp, gpu_uuid, temp, power, util))

conn.commit()
```

**Query with parameters:**
```python
cur.execute("""
    SELECT AVG(gpu_temp) FROM gpu_metrics
    WHERE gpu_uuid = %s AND time > NOW() - INTERVAL '1 hour'
""", (gpu_uuid,))

avg_temp = cur.fetchone()[0]
```

---

### Requests

**What it is:** HTTP library for making web requests in Python.

**How we use it:**

**Scrape DCGM metrics:**
```python
import requests

response = requests.get('http://mock-dcgm:9400/metrics')
prometheus_text = response.text

# Parse Prometheus format
for line in prometheus_text.split('\n'):
    if line.startswith('DCGM_FI_DEV_GPU_TEMP'):
        # Extract: DCGM_FI_DEV_GPU_TEMP{gpu="0"} 67.2
        temp = parse_prometheus_line(line)
```

---

### Pydantic

**What it is:** Data validation using Python type annotations.

**How we use it with FastAPI:**

```python
from pydantic import BaseModel, Field, validator

class GPUMetric(BaseModel):
    gpu_uuid: str = Field(..., regex=r'^GPU-[a-f0-9]{12}$')
    temperature: float = Field(..., ge=0, le=120)  # 0-120°C
    power_usage: float = Field(..., ge=0, le=1000)  # 0-1000W
    
    @validator('temperature')
    def temp_must_be_realistic(cls, v):
        if v > 100:
            raise ValueError('Temperature exceeds safe operating limit')
        return v

# FastAPI auto-validates requests
@app.post("/metrics")
async def ingest_metric(metric: GPUMetric):
    # metric.temperature is guaranteed valid
    pass
```

---

### Joblib

**What it is:** Efficient serialization of Python objects (especially ML models).

**How we use it:**

```python
import joblib

# Save XGBoost model (faster than pickle)
joblib.dump(model, '/models/gpu_predictor.pkl', compress=3)

# Load in production
model = joblib.load('/models/gpu_predictor.pkl')
```

---

### python-snappy

**What it is:** Fast compression library (used by Kafka).

**Why it matters:**
- Compresses GPU metrics before sending to Kafka
- 10,000 GPUs × 100 metrics/sec = 1M messages/sec
- Snappy: 3x smaller, 10x faster than gzip
- Network bandwidth savings: ~70%

---

## 8. GPU Monitoring Foundation

### NVIDIA DCGM (Data Center GPU Manager)

**What it is:** NVIDIA's official tool for managing and monitoring GPUs in datacenters.

**What we simulate in this project:**
- DCGM runs on each GPU node (server with physical GPUs)
- Exposes Prometheus metrics endpoint (port 9400)
- Collects 100+ metrics per GPU every second

**Real DCGM setup:**
```bash
# Install on GPU node
sudo apt install datacenter-gpu-manager

# Start DCGM
sudo systemctl start nvidia-dcgm

# Start Prometheus exporter
dcgm-exporter --port 9400
```

**Metrics DCGM provides (what we simulate):**

**Core metrics:**
- `DCGM_FI_DEV_GPU_TEMP` - GPU temperature (°C)
- `DCGM_FI_DEV_MEMORY_TEMP` - Memory temperature (°C)
- `DCGM_FI_DEV_POWER_USAGE` - Power draw (Watts)
- `DCGM_FI_DEV_TOTAL_ENERGY_CONSUMPTION` - Cumulative energy (mJ)
- `DCGM_FI_DEV_FAN_SPEED` - Fan speed (%)

**Memory:**
- `DCGM_FI_DEV_FB_USED` - Framebuffer used (MB)
- `DCGM_FI_DEV_FB_FREE` - Framebuffer free (MB)
- `DCGM_FI_DEV_FB_TOTAL` - Total memory (MB)

**Errors:**
- `DCGM_FI_DEV_ECC_SBE_VOL_TOTAL` - Single-bit errors (volatile, resets on reboot)
- `DCGM_FI_DEV_ECC_DBE_VOL_TOTAL` - Double-bit errors (critical!)
- `DCGM_FI_DEV_ECC_SBE_AGG_TOTAL` - SBE aggregate (lifetime counter)
- `DCGM_FI_DEV_ECC_DBE_AGG_TOTAL` - DBE aggregate (lifetime counter)

**Performance:**
- `DCGM_FI_PROF_SM_ACTIVE` - Streaming multiprocessor active (%)
- `DCGM_FI_PROF_SM_OCCUPANCY` - SM occupancy (%)
- `DCGM_FI_PROF_PIPE_TENSOR_ACTIVE` - Tensor core active (%)
- `DCGM_FI_PROF_DRAM_ACTIVE` - Memory active (%)
- `DCGM_FI_DEV_GPU_UTIL` - Overall GPU utilization (%)

**Throttling:**
- `DCGM_FI_DEV_CLOCK_THROTTLE_REASONS` - Bitmask (why GPU slowed down)
  - Bit 0: GPU idle
  - Bit 1: SW thermal slowdown
  - Bit 2: HW thermal slowdown
  - Bit 6: SW power cap
  - Bit 7: HW power brake

**NVLink (GPU-to-GPU):**
- `DCGM_FI_PROF_NVLINK_RX_BYTES` - NVLink receive bandwidth
- `DCGM_FI_PROF_NVLINK_TX_BYTES` - NVLink transmit bandwidth

**Clocks:**
- `DCGM_FI_DEV_SM_CLOCK` - SM clock frequency (MHz)
- `DCGM_FI_DEV_MEM_CLOCK` - Memory clock frequency (MHz)

**PCIe:**
- `DCGM_FI_PROF_PCIE_TX_BYTES` - PCIe transmit (CPU→GPU)
- `DCGM_FI_PROF_PCIE_RX_BYTES` - PCIe receive (GPU→CPU)

**Why these metrics matter for A100/H100:**

**Temperature monitoring:**
- A100: 85°C = thermal throttling starts
- H100: 90°C = thermal throttling (better cooling)
- Memory: 95°C = critical (HBM2e/HBM3 limit)

**Power monitoring:**
- A100-SXM4-80GB: 400W TDP
- H100-SXM5-80GB: 700W TDP
- Power spikes indicate training job starts
- Constant max power = potential cooling issues

**ECC errors (memory health):**
- SBE (single-bit errors): Auto-corrected, but increasing rate = failing memory
- DBE (double-bit errors): Uncorrectable = immediate concern
- Industry threshold: >100 SBE/hour = schedule replacement
- Any DBE = investigate immediately

**Throttle reasons (performance issues):**
- Thermal throttle: GPU reducing speed to cool down
- Power throttle: Hit power limit (training jobs too aggressive)
- Both = cooling problem or inadequate power delivery

**NVLink bandwidth (multi-GPU training):**
- A100: 600 GB/s (12 links × 50 GB/s each)
- H100: 900 GB/s (18 links × 50 GB/s each)
- Low bandwidth during training = NVLink fault or topology issue

**Real-world DCGM deployment:**

**Single GPU node:**
```
┌─────────────────────────┐
│  GPU Node (8× H100)     │
│  ┌──────────────────┐   │
│  │ DCGM Agent       │   │
│  │ (port 5555)      │   │
│  └──────────────────┘   │
│          ↓              │
│  ┌──────────────────┐   │
│  │ DCGM Exporter    │   │
│  │ (port 9400)      │   │
│  └──────────────────┘   │
│          ↓              │
│     [Prometheus         │
│      formatted          │
│      metrics]           │
└─────────────────────────┘
         ↓
    Collector scrapes
    every 10 seconds
```

**Multi-node cluster:**
```
Node 1 (8× A100) → DCGM → :9400
Node 2 (8× A100) → DCGM → :9400
Node 3 (8× H100) → DCGM → :9400
Node 4 (8× H100) → DCGM → :9400
        ↓
   Collectors (one per node)
        ↓
      Kafka
        ↓
   TimescaleDB
```

**Our mock DCGM:**
```python
# Simulates realistic GPU behavior
class GPUSimulator:
    def get_temperature(self):
        intensity = self.get_workload_intensity()
        base = self.profile['base_temp']
        age_factor = 1.0 + (self.profile['age_months'] / 12) * 0.1
        temp = base * age_factor + (intensity * 15.0) + random.gauss(0, 1.5)
        return max(30, min(95, temp))
    
    def get_power_usage(self):
        intensity = self.get_workload_intensity()
        base = self.profile['base_power']
        power = (base + (intensity * 100.0)) + random.gauss(0, 5)
        return power
    
    # ... (20+ more realistic simulations)
```

---

## 9. Development & Deployment

### Cloud-init

**What it is:** Industry-standard way to customize Linux VMs on first boot.

**How we use it:**
```yaml
#cloud-config

packages:
  - docker-ce
  - docker-compose-plugin

runcmd:
  # Install Docker
  - curl -fsSL https://get.docker.com | sh
  
  # Add user to docker group
  - usermod -aG docker azureuser
  
  # Create app directory
  - mkdir -p /opt/gpu-health-monitor
  - chown azureuser:azureuser /opt/gpu-health-monitor

final_message: "VM ready for GPU monitoring deployment!"
```

**Azure creates VM → cloud-init runs → Docker installed → we deploy app**

---

### Azure Services

**What we use:**

**1. Azure Virtual Machines:**
- Standard_DC1ds_v3 (1 vCPU, 8 GB RAM)
- Enough for 10 simulated GPUs + full monitoring stack
- For real deployment: GPU-enabled VMs (NC-series, ND-series)

**2. Azure Virtual Network:**
- Private network (10.0.0.0/16)
- Subnet for VMs (10.0.1.0/24)

**3. Network Security Group:**
- SSH (port 22): Management access
- Grafana (port 3000): Dashboard access
- In production: VPN-only access, no public IPs

**4. Public IP:**
- Static IP for demo
- In production: Load balancer with private IPs

---

### Git & GitHub

**Version control for:**
- Infrastructure code (Terraform)
- Application code (Python services)
- Configuration (docker-compose, Grafana dashboards)
- Documentation

**Branch strategy:**
- `main`: Production-ready code
- Feature branches for development
- Tags for releases

---

## Summary: The Complete Stack

```
┌─────────────────────────────────────────────────────────────┐
│                     GPU Health Monitor                       │
│                   Technology Stack Map                       │
└─────────────────────────────────────────────────────────────┘

Infrastructure Layer:
├─ Docker (17 containers)
├─ Docker Compose (orchestration)
├─ Terraform (Azure IaC)
└─ Azure (cloud provider)

Data Layer:
├─ Apache Kafka (event streaming)
├─ Apache Zookeeper (coordination)
└─ TimescaleDB/PostgreSQL (time-series + relational)

Visualization Layer:
├─ Grafana (dashboards, 6 total)
└─ Adminer (database management)

ML Layer:
├─ XGBoost (failure prediction)
├─ MLflow (experiment tracking)
├─ Scikit-learn (preprocessing, evaluation)
├─ Pandas (data manipulation)
├─ NumPy (numerical computing)
└─ SciPy (signal processing, statistics)

Application Layer:
├─ FastAPI + Uvicorn (REST API)
├─ Flask (mock DCGM exporter)
└─ Python services (collectors, processors, predictors)

Python Libraries:
├─ kafka-python (Kafka client)
├─ psycopg2 (PostgreSQL driver)
├─ requests (HTTP client)
├─ pydantic (data validation)
├─ joblib (model serialization)
└─ python-snappy (compression)

GPU Monitoring:
└─ NVIDIA DCGM (simulated, 100+ metrics/GPU)

Development:
├─ Git/GitHub (version control)
├─ Cloud-init (VM bootstrapping)
└─ Azure CLI (cloud management)
```

---

## Scaling to Production: 10,000 GPU Fleet

**Infrastructure:**
- 1,000 GPU nodes (10 GPUs each)
- 5 Kafka brokers (3-5 TB RAM total)
- TimescaleDB cluster (10 nodes, sharded by datacenter)
- 50 collector instances (autoscaled)
- 10 validator instances
- 5 ML predictor instances

**Data volume:**
```
10,000 GPUs × 100 metrics/sec × 86,400 sec/day
= 86.4 billion metrics/day
= 3.5 TB/day raw data
= 350 GB/day compressed (TimescaleDB)
```

**Cost (AWS/Azure):**
- Compute: $50,000/month (VMs, containers)
- Storage: $5,000/month (1 year retention)
- Network: $2,000/month (inter-AZ transfers)
**Total: ~$57k/month** to monitor $50M+ GPU fleet

**ROI:**
- Prevent 1 H100 failure/month = $30k saved
- Reduce downtime 10% = $100k+ saved
- Early replacement warnings = Better capacity planning
**ROI: 3-5x** monitoring cost

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-13  
**Maintained by:** GPU Health Monitor Project

---

## What Next?

This document covers the "what" and "why" of every technology. For "how to use":

1. **Quick Start:** `docs/quick-start.md`
2. **Architecture:** `docs/architecture/`
3. **Database Schema:** `docs/database-tables-explained.md`
4. **ML Tech Stack:** `docs/ml-tech-stack.md`
5. **Deployment:** `terraform/README.md`
