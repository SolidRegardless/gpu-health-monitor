# GPU Health System - Proof of Concept Implementation Guide

**Version:** 1.0  
**Date:** 2026-02-09  
**Duration:** 6 weeks  
**Scope:** 50 GPUs pilot deployment

---

## Executive Summary

This document provides step-by-step implementation instructions for the 6-week proof of concept deployment of the GPU Health & Reliability System. The POC will validate core technical assumptions, demonstrate economic value, and de-risk the full fleet rollout.

**POC Goals:**
1. Prove telemetry collection works at scale (50 GPUs, 10s intervals)
2. Validate health scoring against real GPU conditions
3. Demonstrate predictive capability (even if simplified)
4. Show measurable economic ROI potential

**Expected Outcomes:**
- Working monitoring system for 50 GPUs
- Health scores calculated and validated
- At least 1 degraded GPU identified proactively
- Economic model showing 5x+ ROI potential

---

## Week 1: Infrastructure Setup

### Day 1-2: Hardware & Network Preparation

**Objective:** Prepare pilot GPU rack and network connectivity

**Tasks:**

1. **Select 50 Pilot GPUs**
   ```bash
   # Criteria for selection:
   # - Mix of ages (0-36 months)
   # - Mix of models (A100, H100)
   # - Include 3-5 known "problematic" GPUs (high temp, ECC errors)
   # - Include 10+ known "healthy" GPUs (baseline)
   # - All in single datacenter for POC simplicity
   ```

2. **Network Configuration**
   - Ensure all hosts have outbound connectivity to Kafka broker
   - Open required ports: 9092 (Kafka), 5432 (PostgreSQL), 8086 (InfluxDB fallback)
   - Set up dedicated VLAN for monitoring traffic (optional but recommended)
   - Configure DNS entries for monitoring infrastructure

3. **Verify DCGM Accessibility**
   ```bash
   # On each GPU host, verify DCGM is accessible
   ssh gpu-host-01
   nvidia-smi
   dcgmi discovery -l  # Should list all GPUs on host
   
   # If DCGM not installed:
   # Ubuntu/Debian:
   sudo apt-get install datacenter-gpu-manager
   
   # RHEL/CentOS:
   sudo yum install datacenter-gpu-manager
   ```

**Deliverables:**
- List of 50 pilot GPU IDs with metadata (age, model, known issues)
- Network diagram showing monitoring traffic flow
- DCGM verified on all hosts

### Day 3-4: Core Infrastructure Deployment

**Objective:** Deploy Kafka, TimescaleDB, PostgreSQL on single server

**Hardware Requirements for POC Server:**
- CPU: 16 cores
- RAM: 64 GB
- Storage: 2 TB NVMe SSD
- Network: 10 Gbps
- OS: Ubuntu 22.04 LTS

**Deployment Steps:**

1. **Docker & Docker Compose Setup**
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   
   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

2. **Create Docker Compose Configuration**
   ```yaml
   # docker-compose.yml
   version: '3.8'
   
   services:
     zookeeper:
       image: confluentinc/cp-zookeeper:7.5.0
       environment:
         ZOOKEEPER_CLIENT_PORT: 2181
         ZOOKEEPER_TICK_TIME: 2000
       volumes:
         - zookeeper-data:/var/lib/zookeeper/data
         - zookeeper-logs:/var/lib/zookeeper/log
     
     kafka:
       image: confluentinc/cp-kafka:7.5.0
       depends_on:
         - zookeeper
       ports:
         - "9092:9092"
       environment:
         KAFKA_BROKER_ID: 1
         KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
         KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
         KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
         KAFKA_LOG_RETENTION_HOURS: 168  # 7 days
       volumes:
         - kafka-data:/var/lib/kafka/data
     
     timescaledb:
       image: timescale/timescaledb:latest-pg15
       ports:
         - "5432:5432"
       environment:
         POSTGRES_DB: gpu_health
         POSTGRES_USER: gpuhealth
         POSTGRES_PASSWORD: change_me_in_production
       volumes:
         - timescale-data:/var/lib/postgresql/data
       command: postgres -c shared_preload_libraries=timescaledb -c max_connections=200
     
     postgres:
       image: postgres:15
       ports:
         - "5433:5432"
       environment:
         POSTGRES_DB: gpu_assets
         POSTGRES_USER: gpuhealth
         POSTGRES_PASSWORD: change_me_in_production
       volumes:
         - postgres-data:/var/lib/postgresql/data
     
     redis:
       image: redis:7-alpine
       ports:
         - "6379:6379"
       volumes:
         - redis-data:/data
     
     grafana:
       image: grafana/grafana:latest
       ports:
         - "3000:3000"
       environment:
         GF_SECURITY_ADMIN_PASSWORD: admin
         GF_INSTALL_PLUGINS: grafana-clock-panel
       volumes:
         - grafana-data:/var/lib/grafana
   
   volumes:
     zookeeper-data:
     zookeeper-logs:
     kafka-data:
     timescale-data:
     postgres-data:
     redis-data:
     grafana-data:
   ```

3. **Start Infrastructure**
   ```bash
   docker-compose up -d
   
   # Verify all services are running
   docker-compose ps
   
   # Check logs
   docker-compose logs -f kafka
   docker-compose logs -f timescaledb
   ```

4. **Initialize Databases**
   ```bash
   # Connect to TimescaleDB and create schema
   docker exec -it gpu-health-poc-timescaledb-1 psql -U gpuhealth -d gpu_health
   
   # Create hypertable for metrics (see schema below)
   ```

**TimescaleDB Schema:**
```sql
-- gpu_health_metrics.sql
CREATE TABLE gpu_health_metrics (
    time TIMESTAMPTZ NOT NULL,
    gpu_id TEXT NOT NULL,
    host_id TEXT NOT NULL,
    
    -- Temperature (Celsius)
    temp_gpu SMALLINT,
    temp_memory SMALLINT,
    temp_hotspot SMALLINT,
    
    -- Power (Watts)
    power_draw SMALLINT,
    power_limit SMALLINT,
    
    -- Utilization (%)
    util_gpu SMALLINT,
    util_memory SMALLINT,
    
    -- Memory
    memory_used BIGINT,
    memory_total BIGINT,
    ecc_correctable BIGINT,
    ecc_uncorrectable BIGINT,
    
    -- Clocks (MHz)
    clock_gpu SMALLINT,
    clock_memory SMALLINT,
    throttle_reason BIGINT
);

-- Convert to hypertable (partitioned by time)
SELECT create_hypertable('gpu_health_metrics', 'time');

-- Create indexes for common queries
CREATE INDEX idx_gpu_id ON gpu_health_metrics (gpu_id, time DESC);
CREATE INDEX idx_host_id ON gpu_health_metrics (host_id, time DESC);

-- Create continuous aggregate for 1-minute averages
CREATE MATERIALIZED VIEW gpu_metrics_1min
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 minute', time) AS bucket,
       gpu_id,
       host_id,
       AVG(temp_gpu) as avg_temp_gpu,
       MAX(temp_gpu) as max_temp_gpu,
       AVG(power_draw) as avg_power,
       SUM(ecc_correctable) as total_ecc_correctable,
       SUM(ecc_uncorrectable) as total_ecc_uncorrectable,
       AVG(util_gpu) as avg_util_gpu
FROM gpu_health_metrics
GROUP BY bucket, gpu_id, host_id;

-- Refresh policy (refresh every 1 minute)
SELECT add_continuous_aggregate_policy('gpu_metrics_1min',
  start_offset => INTERVAL '2 minutes',
  end_offset => INTERVAL '1 minute',
  schedule_interval => INTERVAL '1 minute');
```

**PostgreSQL Asset Schema:**
```sql
-- Connect to asset database
-- docker exec -it gpu-health-poc-postgres-1 psql -U gpuhealth -d gpu_assets

CREATE TABLE gpu_assets (
    gpu_id TEXT PRIMARY KEY,
    serial_number TEXT UNIQUE,
    model TEXT NOT NULL,  -- 'A100-80GB', 'H100-SXM'
    pci_bus_id TEXT NOT NULL,
    host_id TEXT NOT NULL,
    datacenter TEXT NOT NULL,
    rack_id TEXT,
    
    deployed_date DATE NOT NULL,
    age_days INTEGER GENERATED ALWAYS AS (CURRENT_DATE - deployed_date) STORED,
    
    status TEXT NOT NULL DEFAULT 'active',
    known_issues TEXT[],
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_gpu_status ON gpu_assets(status);
CREATE INDEX idx_gpu_model ON gpu_assets(model);

-- Insert pilot GPU data (example)
INSERT INTO gpu_assets (gpu_id, serial_number, model, pci_bus_id, host_id, datacenter, deployed_date, known_issues)
VALUES 
  ('GPU-A100-001', 'SN12345', 'A100-80GB', '0000:17:00.0', 'host-01', 'DC1', '2023-06-01', ARRAY['high_temp']),
  ('GPU-A100-002', 'SN12346', 'A100-80GB', '0000:65:00.0', 'host-01', 'DC1', '2023-06-01', NULL),
  ('GPU-H100-001', 'SN54321', 'H100-SXM', '0000:17:00.0', 'host-02', 'DC1', '2024-01-15', NULL);
  -- ... add all 50 pilot GPUs
```

**Deliverables:**
- All infrastructure services running and healthy
- Databases initialized with schemas
- Grafana accessible at http://monitoring-server:3000

### Day 5: DCGM Exporter Deployment

**Objective:** Deploy metrics collection agents on all 50 pilot GPU hosts

**DCGM Exporter Setup:**

1. **Install DCGM Exporter (per GPU host)**
   ```bash
   # Option 1: Docker (recommended for POC)
   docker run -d --rm \
     --gpus all \
     --name dcgm-exporter \
     --net=host \
     -e DCGM_EXPORTER_INTERVAL=10000 \
     -e DCGM_EXPORTER_COLLECTORS=/etc/dcgm-exporter/default-counters.csv \
     nvcr.io/nvidia/k8s/dcgm-exporter:3.1.8-3.1.5-ubuntu22.04
   
   # Option 2: Binary installation
   wget https://github.com/NVIDIA/dcgm-exporter/releases/download/3.1.8-3.1.5/dcgm-exporter
   chmod +x dcgm-exporter
   sudo mv dcgm-exporter /usr/local/bin/
   
   # Create systemd service
   sudo tee /etc/systemd/system/dcgm-exporter.service > /dev/null <<EOF
   [Unit]
   Description=NVIDIA DCGM Exporter
   After=network.target
   
   [Service]
   ExecStart=/usr/local/bin/dcgm-exporter -f /etc/dcgm-exporter/metrics.csv
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   EOF
   
   sudo systemctl enable dcgm-exporter
   sudo systemctl start dcgm-exporter
   ```

2. **Verify DCGM Metrics**
   ```bash
   # DCGM exporter listens on :9400 by default
   curl http://localhost:9400/metrics | grep DCGM
   
   # Should see output like:
   # DCGM_FI_DEV_GPU_TEMP{gpu="0",UUID="GPU-..."} 65
   # DCGM_FI_DEV_POWER_USAGE{gpu="0",UUID="GPU-..."} 310
   # etc.
   ```

3. **Create Collection Script**
   ```python
   # gpu_collector.py - Simple collector that pushes to Kafka
   import requests
   import json
   import time
   from kafka import KafkaProducer
   from datetime import datetime
   
   DCGM_ENDPOINT = "http://localhost:9400/metrics"
   KAFKA_BROKER = "monitoring-server:9092"
   KAFKA_TOPIC = "gpu-metrics-raw"
   
   producer = KafkaProducer(
       bootstrap_servers=[KAFKA_BROKER],
       value_serializer=lambda v: json.dumps(v).encode('utf-8')
   )
   
   def parse_dcgm_metrics(text):
       """Parse Prometheus format metrics from DCGM exporter"""
       metrics = {}
       for line in text.split('\n'):
           if line.startswith('#') or not line.strip():
               continue
           if 'DCGM_FI' in line:
               parts = line.split()
               metric_name = parts[0].split('{')[0]
               labels = parts[0].split('{')[1].split('}')[0]
               value = float(parts[1])
               
               # Extract GPU ID from labels
               gpu_id = None
               for label in labels.split(','):
                   if 'UUID=' in label:
                       gpu_id = label.split('=')[1].strip('"')
               
               if gpu_id:
                   if gpu_id not in metrics:
                       metrics[gpu_id] = {}
                   metrics[gpu_id][metric_name] = value
       return metrics
   
   def collect_and_send():
       """Collect metrics and send to Kafka"""
       try:
           response = requests.get(DCGM_ENDPOINT, timeout=5)
           response.raise_for_status()
           
           metrics = parse_dcgm_metrics(response.text)
           timestamp = datetime.utcnow().isoformat()
           
           for gpu_id, gpu_metrics in metrics.items():
               message = {
                   'timestamp': timestamp,
                   'gpu_id': gpu_id,
                   'host_id': os.uname().nodename,
                   'metrics': gpu_metrics
               }
               producer.send(KAFKA_TOPIC, value=message)
           
           producer.flush()
           print(f"Sent metrics for {len(metrics)} GPUs at {timestamp}")
       
       except Exception as e:
           print(f"Error collecting metrics: {e}")
   
   if __name__ == "__main__":
       print(f"Starting GPU metrics collector...")
       print(f"DCGM endpoint: {DCGM_ENDPOINT}")
       print(f"Kafka broker: {KAFKA_BROKER}")
       
       while True:
           collect_and_send()
           time.sleep(10)  # Collect every 10 seconds
   ```

4. **Deploy Collector on All Hosts**
   ```bash
   # Create deployment script
   for host in gpu-host-{01..10}; do
       echo "Deploying to $host..."
       scp gpu_collector.py $host:/opt/gpu-collector/
       ssh $host "cd /opt/gpu-collector && python3 gpu_collector.py &"
   done
   ```

**Deliverables:**
- DCGM exporters running on all 50 GPU hosts
- Collectors sending data to Kafka every 10 seconds
- Verify data flow: DCGM → Collector → Kafka

---

## Week 2: Data Pipeline & Validation

### Day 6-7: Stream Processing

**Objective:** Process raw Kafka metrics into TimescaleDB

**Kafka Consumer & DB Writer:**

```python
# stream_processor.py
import json
import psycopg2
from kafka import KafkaConsumer
from datetime import datetime

KAFKA_BROKER = "localhost:9092"
KAFKA_TOPIC = "gpu-metrics-raw"
PG_CONN = "postgresql://gpuhealth:change_me@localhost:5432/gpu_health"

def process_message(message):
    """Transform raw metrics into DB schema"""
    data = message['metrics']
    
    # Map DCGM metric names to our schema
    row = {
        'time': message['timestamp'],
        'gpu_id': message['gpu_id'],
        'host_id': message['host_id'],
        'temp_gpu': data.get('DCGM_FI_DEV_GPU_TEMP'),
        'temp_memory': data.get('DCGM_FI_DEV_MEM_TEMP'),
        'power_draw': data.get('DCGM_FI_DEV_POWER_USAGE'),
        'power_limit': data.get('DCGM_FI_DEV_POWER_LIMIT'),
        'util_gpu': data.get('DCGM_FI_DEV_GPU_UTIL'),
        'util_memory': data.get('DCGM_FI_DEV_MEM_COPY_UTIL'),
        'memory_used': data.get('DCGM_FI_DEV_FB_USED'),
        'memory_total': data.get('DCGM_FI_DEV_FB_TOTAL'),
        'ecc_correctable': data.get('DCGM_FI_DEV_ECC_SBE_VOL_TOTAL', 0),
        'ecc_uncorrectable': data.get('DCGM_FI_DEV_ECC_DBE_VOL_TOTAL', 0),
        'clock_gpu': data.get('DCGM_FI_DEV_SM_CLOCK'),
        'clock_memory': data.get('DCGM_FI_DEV_MEM_CLOCK'),
        'throttle_reason': data.get('DCGM_FI_DEV_CLOCK_THROTTLE_REASONS', 0)
    }
    
    return row

def insert_metrics(conn, rows):
    """Bulk insert metrics into TimescaleDB"""
    cursor = conn.cursor()
    
    insert_query = """
        INSERT INTO gpu_health_metrics (
            time, gpu_id, host_id,
            temp_gpu, temp_memory, power_draw, power_limit,
            util_gpu, util_memory, memory_used, memory_total,
            ecc_correctable, ecc_uncorrectable,
            clock_gpu, clock_memory, throttle_reason
        ) VALUES (
            %(time)s, %(gpu_id)s, %(host_id)s,
            %(temp_gpu)s, %(temp_memory)s, %(power_draw)s, %(power_limit)s,
            %(util_gpu)s, %(util_memory)s, %(memory_used)s, %(memory_total)s,
            %(ecc_correctable)s, %(ecc_uncorrectable)s,
            %(clock_gpu)s, %(clock_memory)s, %(throttle_reason)s
        )
    """
    
    cursor.executemany(insert_query, rows)
    conn.commit()
    print(f"Inserted {len(rows)} rows")

def main():
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=[KAFKA_BROKER],
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest',
        enable_auto_commit=True,
        group_id='stream-processor'
    )
    
    conn = psycopg2.connect(PG_CONN)
    
    batch = []
    batch_size = 100
    
    print("Stream processor started...")
    
    for message in consumer:
        try:
            row = process_message(message.value)
            batch.append(row)
            
            if len(batch) >= batch_size:
                insert_metrics(conn, batch)
                batch = []
        
        except Exception as e:
            print(f"Error processing message: {e}")
    
if __name__ == "__main__":
    main()
```

**Deploy Stream Processor:**
```bash
# Install dependencies
pip3 install kafka-python psycopg2-binary

# Run as service
nohup python3 stream_processor.py > stream_processor.log 2>&1 &
```

**Validation Queries:**
```sql
-- Verify data is flowing
SELECT COUNT(*) FROM gpu_health_metrics WHERE time > NOW() - INTERVAL '5 minutes';

-- Check per-GPU data rate
SELECT gpu_id, COUNT(*) as samples, 
       MIN(time) as first_sample, 
       MAX(time) as last_sample
FROM gpu_health_metrics 
WHERE time > NOW() - INTERVAL '1 hour'
GROUP BY gpu_id
ORDER BY samples DESC;

-- Identify any gaps
SELECT gpu_id,
       time_bucket('1 minute', time) as minute,
       COUNT(*) as samples
FROM gpu_health_metrics
WHERE time > NOW() - INTERVAL '1 hour'
GROUP BY gpu_id, minute
HAVING COUNT(*) < 5  -- Expect 6 samples per minute (10s intervals)
ORDER BY minute DESC;
```

### Day 8-9: Grafana Dashboards

**Objective:** Create real-time monitoring dashboards

**Dashboard 1: Fleet Overview**

```json
{
  "dashboard": {
    "title": "GPU Fleet Overview",
    "panels": [
      {
        "title": "GPU Temperature Distribution",
        "type": "graph",
        "datasource": "TimescaleDB",
        "targets": [
          {
            "rawSql": "SELECT time, gpu_id, temp_gpu FROM gpu_health_metrics WHERE $__timeFilter(time) ORDER BY time"
          }
        ]
      },
      {
        "title": "ECC Errors (24h)",
        "type": "stat",
        "datasource": "TimescaleDB",
        "targets": [
          {
            "rawSql": "SELECT SUM(ecc_correctable) as correctable, SUM(ecc_uncorrectable) as uncorrectable FROM gpu_health_metrics WHERE time > NOW() - INTERVAL '24 hours'"
          }
        ]
      }
    ]
  }
}
```

**Configure Grafana:**
```bash
# Add TimescaleDB as data source
curl -X POST http://admin:admin@localhost:3000/api/datasources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "TimescaleDB",
    "type": "postgres",
    "url": "timescaledb:5432",
    "database": "gpu_health",
    "user": "gpuhealth",
    "secureJsonData": {
      "password": "change_me"
    },
    "jsonData": {
      "sslmode": "disable",
      "postgresVersion": 1500,
      "timescaledb": true
    }
  }'

# Import dashboard from JSON
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @gpu-fleet-dashboard.json
```

**Deliverables:**
- Stream processor running and inserting data
- Grafana dashboards showing real-time metrics
- Data validation queries passing

---

## Week 3-4: Health Scoring Implementation

### Day 10-14: Health Scoring Engine

**Objective:** Implement health scoring algorithm

**Health Scorer Service:**

```python
# health_scorer.py
import psycopg2
from datetime import datetime, timedelta
import time

PG_METRICS = "postgresql://gpuhealth:change_me@localhost:5432/gpu_health"
PG_ASSETS = "postgresql://gpuhealth:change_me@localhost:5433/gpu_assets"

def calculate_thermal_score(gpu_data):
    """Calculate thermal health score (0-100)"""
    score = 100
    
    avg_temp = gpu_data['avg_temp_gpu']
    max_temp = gpu_data['max_temp_gpu']
    throttle_count = gpu_data['throttle_events']
    
    # Penalty for high average temperature
    if avg_temp > 75:
        score -= (avg_temp - 75) * 2
    
    # Penalty for high max temperature
    if max_temp > 85:
        score -= (max_temp - 85) * 5
    
    # Penalty for throttling
    score -= throttle_count * 10
    
    return max(0, min(100, score))

def calculate_memory_score(gpu_data):
    """Calculate memory health score (0-100)"""
    score = 100
    
    correctable_7d = gpu_data['ecc_correctable_7d']
    uncorrectable_7d = gpu_data['ecc_uncorrectable_7d']
    
    # Penalty for correctable errors
    correctable_per_day = correctable_7d / 7
    score -= min(50, correctable_per_day)
    
    # Severe penalty for uncorrectable errors
    if uncorrectable_7d > 0:
        score = min(score, 70)  # Cap at 70 if any uncorrectable
    
    return max(0, min(100, score))

def calculate_power_score(gpu_data):
    """Calculate power health score (0-100)"""
    score = 100
    
    power_variance = gpu_data['power_variance']
    
    # Penalty for high power variance (instability)
    if power_variance > 50:
        score -= (power_variance - 50) / 2
    
    return max(0, min(100, score))

def calculate_overall_score(thermal, memory, power):
    """Weighted average of sub-scores"""
    return round(
        thermal * 0.35 +   # 35% thermal
        memory * 0.45 +    # 45% memory (most critical)
        power * 0.20       # 20% power
    )

def get_gpu_data_7d(conn, gpu_id):
    """Fetch 7-day aggregated data for a GPU"""
    cursor = conn.cursor()
    
    query = """
        SELECT 
            AVG(temp_gpu) as avg_temp_gpu,
            MAX(temp_gpu) as max_temp_gpu,
            SUM(CASE WHEN throttle_reason > 0 THEN 1 ELSE 0 END) as throttle_events,
            SUM(ecc_correctable) as ecc_correctable_7d,
            SUM(ecc_uncorrectable) as ecc_uncorrectable_7d,
            STDDEV(power_draw) as power_variance
        FROM gpu_health_metrics
        WHERE gpu_id = %s
          AND time > NOW() - INTERVAL '7 days'
    """
    
    cursor.execute(query, (gpu_id,))
    row = cursor.fetchone()
    
    return {
        'avg_temp_gpu': row[0] or 0,
        'max_temp_gpu': row[1] or 0,
        'throttle_events': row[2] or 0,
        'ecc_correctable_7d': row[3] or 0,
        'ecc_uncorrectable_7d': row[4] or 0,
        'power_variance': row[5] or 0
    }

def save_health_score(conn, gpu_id, scores):
    """Save health score to database"""
    cursor = conn.cursor()
    
    query = """
        INSERT INTO gpu_health_scores (
            gpu_id, calculated_at, overall_score,
            thermal_score, memory_score, power_score
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    cursor.execute(query, (
        gpu_id,
        datetime.utcnow(),
        scores['overall'],
        scores['thermal'],
        scores['memory'],
        scores['power']
    ))
    conn.commit()

def score_all_gpus():
    """Calculate health scores for all GPUs"""
    conn_metrics = psycopg2.connect(PG_METRICS)
    conn_assets = psycopg2.connect(PG_ASSETS)
    
    # Create health scores table if not exists
    cursor = conn_assets.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gpu_health_scores (
            gpu_id TEXT NOT NULL,
            calculated_at TIMESTAMP NOT NULL,
            overall_score SMALLINT NOT NULL,
            thermal_score SMALLINT NOT NULL,
            memory_score SMALLINT NOT NULL,
            power_score SMALLINT NOT NULL,
            PRIMARY KEY (gpu_id, calculated_at)
        )
    """)
    conn_assets.commit()
    
    # Get list of all GPUs
    cursor.execute("SELECT gpu_id FROM gpu_assets WHERE status = 'active'")
    gpu_ids = [row[0] for row in cursor.fetchall()]
    
    print(f"Scoring {len(gpu_ids)} GPUs...")
    
    for gpu_id in gpu_ids:
        try:
            # Fetch data
            gpu_data = get_gpu_data_7d(conn_metrics, gpu_id)
            
            # Calculate scores
            thermal = calculate_thermal_score(gpu_data)
            memory = calculate_memory_score(gpu_data)
            power = calculate_power_score(gpu_data)
            overall = calculate_overall_score(thermal, memory, power)
            
            scores = {
                'overall': overall,
                'thermal': thermal,
                'memory': memory,
                'power': power
            }
            
            # Save
            save_health_score(conn_assets, gpu_id, scores)
            
            print(f"{gpu_id}: Overall={overall}, Thermal={thermal}, Memory={memory}, Power={power}")
        
        except Exception as e:
            print(f"Error scoring {gpu_id}: {e}")
    
    conn_metrics.close()
    conn_assets.close()

if __name__ == "__main__":
    while True:
        print(f"\n=== Health Scoring Run: {datetime.now()} ===")
        score_all_gpus()
        print("Sleeping for 15 minutes...")
        time.sleep(900)  # Run every 15 minutes
```

**Deploy Health Scorer:**
```bash
nohup python3 health_scorer.py > health_scorer.log 2>&1 &
```

**Validation Queries:**
```sql
-- View latest health scores
SELECT gpu_id, overall_score, thermal_score, memory_score, power_score, calculated_at
FROM gpu_health_scores
WHERE calculated_at > NOW() - INTERVAL '1 hour'
ORDER BY overall_score ASC
LIMIT 20;

-- Identify degraded GPUs
SELECT gpu_id, overall_score, thermal_score, memory_score
FROM gpu_health_scores
WHERE calculated_at = (SELECT MAX(calculated_at) FROM gpu_health_scores)
  AND overall_score < 70
ORDER BY overall_score ASC;

-- Health score distribution
SELECT 
    CASE 
        WHEN overall_score >= 90 THEN '90-100 Excellent'
        WHEN overall_score >= 80 THEN '80-89 Good'
        WHEN overall_score >= 70 THEN '70-79 Fair'
        WHEN overall_score >= 60 THEN '60-69 Degraded'
        ELSE '<60 Poor'
    END as health_category,
    COUNT(*) as count
FROM gpu_health_scores
WHERE calculated_at = (SELECT MAX(calculated_at) FROM gpu_health_scores)
GROUP BY health_category
ORDER BY health_category DESC;
```

### Day 15-18: Validation & Refinement

**Objective:** Validate health scores against known GPU conditions

**Validation Process:**

1. **Compare Against Known Issues**
   ```sql
   -- GPUs with known issues should have lower scores
   SELECT a.gpu_id, a.known_issues, h.overall_score
   FROM gpu_assets a
   JOIN gpu_health_scores h ON a.gpu_id = h.gpu_id
   WHERE a.known_issues IS NOT NULL
     AND h.calculated_at = (SELECT MAX(calculated_at) FROM gpu_health_scores)
   ORDER BY h.overall_score ASC;
   
   -- Expected: GPUs with 'high_temp' should have low thermal scores
   -- Expected: GPUs with 'ecc_errors' should have low memory scores
   ```

2. **Operator Review**
   - Present top 10 "degraded" GPUs (lowest scores) to operators
   - Ask: "Do you recognize these GPUs as problematic?"
   - Document: True positives vs false positives

3. **Score Tuning**
   - Adjust weights if needed (thermal/memory/power)
   - Adjust penalty thresholds based on feedback
   - Rerun scoring and re-validate

**Deliverables:**
- Health scores calculated for all 50 GPUs every 15 minutes
- Validation report showing accuracy vs known issues
- Grafana dashboard with health score visualization

---

## Week 5: Predictive Modeling (Simplified)

### Day 19-21: Feature Engineering

**Objective:** Create features for failure prediction

**Feature Extraction:**

```python
# feature_engineering.py
import psycopg2
import pandas as pd
from datetime import datetime, timedelta

def extract_features(gpu_id, lookback_days=30):
    """Extract predictive features for a GPU"""
    conn = psycopg2.connect("postgresql://gpuhealth:change_me@localhost:5432/gpu_health")
    
    # Fetch metrics for last N days
    query = """
        SELECT time, temp_gpu, power_draw, ecc_correctable, ecc_uncorrectable,
               util_gpu, clock_gpu, throttle_reason
        FROM gpu_health_metrics
        WHERE gpu_id = %s
          AND time > NOW() - INTERVAL '%s days'
        ORDER BY time
    """
    
    df = pd.read_sql(query, conn, params=(gpu_id, lookback_days))
    conn.close()
    
    if len(df) == 0:
        return None
    
    # Calculate features
    features = {
        'gpu_id': gpu_id,
        
        # Temperature features
        'temp_mean_7d': df['temp_gpu'].tail(7*24*6).mean(),  # 7 days, 6 samples/hour
        'temp_max_7d': df['temp_gpu'].tail(7*24*6).max(),
        'temp_std_7d': df['temp_gpu'].tail(7*24*6).std(),
        'temp_mean_30d': df['temp_gpu'].mean(),
        'temp_max_30d': df['temp_gpu'].max(),
        
        # ECC error features
        'ecc_correctable_7d': df['ecc_correctable'].tail(7*24*6).sum(),
        'ecc_correctable_30d': df['ecc_correctable'].sum(),
        'ecc_uncorrectable_7d': df['ecc_uncorrectable'].tail(7*24*6).sum(),
        'ecc_uncorrectable_30d': df['ecc_uncorrectable'].sum(),
        
        # ECC trend (errors per day, last 7 days)
        'ecc_rate_7d': df['ecc_correctable'].tail(7*24*6).sum() / 7,
        
        # Power features
        'power_mean_7d': df['power_draw'].tail(7*24*6).mean(),
        'power_std_7d': df['power_draw'].tail(7*24*6).std(),
        
        # Throttling
        'throttle_events_7d': (df['throttle_reason'].tail(7*24*6) > 0).sum(),
        
        # Utilization variance (workload stability)
        'util_std_7d': df['util_gpu'].tail(7*24*6).std(),
        
        # Clock stability
        'clock_std_7d': df['clock_gpu'].tail(7*24*6).std()
    }
    
    return features

def create_feature_dataset(gpu_ids):
    """Create feature dataset for all GPUs"""
    features_list = []
    
    for gpu_id in gpu_ids:
        features = extract_features(gpu_id)
        if features:
            features_list.append(features)
    
    return pd.DataFrame(features_list)

if __name__ == "__main__":
    # Get all active GPUs
    conn = psycopg2.connect("postgresql://gpuhealth:change_me@localhost:5433/gpu_assets")
    cursor = conn.cursor()
    cursor.execute("SELECT gpu_id FROM gpu_assets WHERE status = 'active'")
    gpu_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Extract features
    features_df = create_feature_dataset(gpu_ids)
    
    # Save to CSV
    features_df.to_csv('gpu_features.csv', index=False)
    print(f"Extracted features for {len(features_df)} GPUs")
    print(features_df.head())
```

### Day 22-25: Simple Prediction Model

**Objective:** Build simplified failure prediction model

**Note:** Since POC may not have actual failures, we'll create a "risk score" based on health degradation patterns.

**Risk Scoring Model:**

```python
# risk_model.py
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

def calculate_risk_score(features_df):
    """Calculate failure risk score (0-100) for each GPU"""
    
    df = features_df.copy()
    
    # Define risk factors with weights
    risk_components = []
    
    # 1. ECC error risk (40% of total risk)
    ecc_risk = np.clip(
        df['ecc_correctable_7d'] / 50 * 100,  # Normalize: 50 errors = 100% risk
        0, 100
    ) * 0.4
    risk_components.append(ecc_risk)
    
    # Any uncorrectable = automatic high risk
    df.loc[df['ecc_uncorrectable_7d'] > 0, 'ecc_risk_bonus'] = 30
    risk_components.append(df.get('ecc_risk_bonus', 0))
    
    # 2. Thermal risk (30% of total risk)
    thermal_risk = np.clip(
        (df['temp_max_7d'] - 75) / 20 * 100,  # 75-95C mapped to 0-100%
        0, 100
    ) * 0.3
    risk_components.append(thermal_risk)
    
    # 3. Throttling risk (20% of total risk)
    throttle_risk = np.clip(
        df['throttle_events_7d'] / 10 * 100,  # 10 events = 100% risk
        0, 100
    ) * 0.2
    
    risk_components.append(throttle_risk)
    
    # 4. Power instability risk (10% of total risk)
    power_risk = np.clip(
        df['power_std_7d'] / 50 * 100,  # StdDev 50W = 100% risk
        0, 100
    ) * 0.1
    risk_components.append(power_risk)
    
    # Combine all risk components
    total_risk = sum(risk_components)
    total_risk = np.clip(total_risk, 0, 100)
    
    # Add to dataframe
    df['risk_score'] = total_risk.round(0).astype(int)
    
    # Classify risk level
    df['risk_level'] = pd.cut(
        df['risk_score'],
        bins=[0, 25, 50, 75, 100],
        labels=['low', 'medium', 'high', 'critical']
    )
    
    return df[['gpu_id', 'risk_score', 'risk_level', 'ecc_correctable_7d', 'temp_max_7d', 'throttle_events_7d']]

if __name__ == "__main__":
    # Load features
    features = pd.read_csv('gpu_features.csv')
    
    # Calculate risk scores
    risk_df = calculate_risk_score(features)
    
    # Save results
    risk_df.to_csv('gpu_risk_scores.csv', index=False)
    
    # Show summary
    print("\n=== Risk Distribution ===")
    print(risk_df['risk_level'].value_counts())
    
    print("\n=== Top 10 At-Risk GPUs ===")
    print(risk_df.nlargest(10, 'risk_score'))
```

**Store Risk Scores in Database:**

```sql
-- Create risk scores table
CREATE TABLE gpu_risk_scores (
    gpu_id TEXT NOT NULL,
    calculated_at TIMESTAMP NOT NULL,
    risk_score SMALLINT NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    PRIMARY KEY (gpu_id, calculated_at)
);
```

```python
# Save risk scores to database
import psycopg2

def save_risk_scores(risk_df):
    conn = psycopg2.connect("postgresql://gpuhealth:change_me@localhost:5433/gpu_assets")
    cursor = conn.cursor()
    
    for _, row in risk_df.iterrows():
        cursor.execute("""
            INSERT INTO gpu_risk_scores (gpu_id, calculated_at, risk_score, risk_level)
            VALUES (%s, %s, %s, %s)
        """, (row['gpu_id'], datetime.utcnow(), row['risk_score'], row['risk_level']))
    
    conn.commit()
    conn.close()
```

**Deliverables:**
- Feature extraction pipeline working
- Risk scores calculated for all 50 GPUs
- Top 10 "at-risk" GPUs identified

---

## Week 6: Economic Modeling & POC Demo

### Day 26-28: Economic Model

**Objective:** Demonstrate economic value of health monitoring

**Simple Economic Calculator:**

```python
# economic_model.py
import pandas as pd

def calculate_economic_value(gpu_id, health_score, risk_score, model='H100-SXM'):
    """Calculate economic metrics for a GPU"""
    
    # Constants (example values)
    GPU_PURCHASE_PRICE = {
        'H100-SXM': 40000,
        'A100-80GB': 15000
    }
    
    HOURLY_RENTAL_RATE = {
        'H100-SXM': 3.50,
        'A100-80GB': 1.50
    }
    
    MONTHLY_OPERATIONAL_COST = {
        'base_power': 60,      # Power cost
        'base_cooling': 18,    # Cooling cost
        'base_rack': 100,      # Rack space
        'base_maintenance': 50 # Maintenance
    }
    
    # Calculate residual value based on health
    base_price = GPU_PURCHASE_PRICE[model]
    health_multiplier = 0.5 + (health_score / 100) * 0.7  # 0.5 - 1.2
    residual_value = base_price * health_multiplier
    
    # Calculate monthly revenue potential
    hourly_rate = HOURLY_RENTAL_RATE[model]
    
    if health_score >= 85:
        utilization = 0.90
    elif health_score >= 70:
        utilization = 0.75
    elif health_score >= 50:
        utilization = 0.50
    else:
        utilization = 0.25
    
    monthly_hours = 730
    monthly_revenue = hourly_rate * monthly_hours * utilization
    
    # Calculate operational costs (increase with poor health)
    health_penalty = (100 - health_score) * 2  # $2 per health point below 100
    monthly_cost = sum(MONTHLY_OPERATIONAL_COST.values()) + health_penalty
    
    # Calculate NPV of keeping in production (12 months)
    npv_keep_12m = (monthly_revenue - monthly_cost) * 12
    
    # Decision recommendation
    if health_score >= 70 and npv_keep_12m > residual_value:
        recommendation = "KEEP"
        expected_value = npv_keep_12m
    elif residual_value > 0.5 * base_price:
        recommendation = "SELL"
        expected_value = residual_value * 0.95  # -5% transaction cost
    else:
        recommendation = "DECOMMISSION"
        expected_value = base_price * 0.10  # 10% salvage value
    
    return {
        'gpu_id': gpu_id,
        'model': model,
        'health_score': health_score,
        'risk_score': risk_score,
        'residual_value': round(residual_value, 2),
        'monthly_revenue': round(monthly_revenue, 2),
        'monthly_cost': round(monthly_cost, 2),
        'monthly_profit': round(monthly_revenue - monthly_cost, 2),
        'npv_keep_12m': round(npv_keep_12m, 2),
        'recommendation': recommendation,
        'expected_value': round(expected_value, 2)
    }

if __name__ == "__main__":
    # Load health and risk scores
    health_df = pd.read_sql(
        "SELECT gpu_id, overall_score FROM gpu_health_scores WHERE calculated_at = (SELECT MAX(calculated_at) FROM gpu_health_scores)",
        conn
    )
    
    risk_df = pd.read_sql(
        "SELECT gpu_id, risk_score FROM gpu_risk_scores WHERE calculated_at = (SELECT MAX(calculated_at) FROM gpu_risk_scores)",
        conn
    )
    
    assets_df = pd.read_sql(
        "SELECT gpu_id, model FROM gpu_assets",
        conn
    )
    
    # Merge
    df = health_df.merge(risk_df, on='gpu_id').merge(assets_df, on='gpu_id')
    
    # Calculate economic value for each GPU
    results = []
    for _, row in df.iterrows():
        econ = calculate_economic_value(
            row['gpu_id'],
            row['overall_score'],
            row['risk_score'],
            row['model']
        )
        results.append(econ)
    
    econ_df = pd.DataFrame(results)
    
    # Save results
    econ_df.to_csv('economic_analysis.csv', index=False)
    
    # Print summary
    print("\n=== Economic Summary ===")
    print(f"Total Fleet Value: ${econ_df['residual_value'].sum():,.2f}")
    print(f"Monthly Revenue Potential: ${econ_df['monthly_revenue'].sum():,.2f}")
    print(f"Monthly Operational Cost: ${econ_df['monthly_cost'].sum():,.2f}")
    print(f"Monthly Profit: ${econ_df['monthly_profit'].sum():,.2f}")
    
    print("\n=== Recommendations ===")
    print(econ_df['recommendation'].value_counts())
    
    print("\n=== GPUs Recommended for Sale ===")
    print(econ_df[econ_df['recommendation'] == 'SELL'][['gpu_id', 'health_score', 'residual_value']])
```

### Day 29-30: POC Demo & Documentation

**Objective:** Prepare final POC presentation

**Demo Dashboard (Grafana):**

Create comprehensive dashboard showing:
1. Fleet health overview (50 GPUs)
2. Health score distribution
3. Risk score distribution
4. Economic recommendations
5. Identified issues (ECC errors, thermal, etc.)

**POC Report Structure:**

```markdown
# GPU Health System - POC Results

## Executive Summary
- Deployed on 50 GPUs for 6 weeks
- Collected X million metric samples
- Identified Y degraded GPUs proactively
- Demonstrated $Z economic value

## Technical Achievements
- ✅ Metrics collection: 99.X% uptime
- ✅ Health scoring: All 50 GPUs scored every 15min
- ✅ Risk prediction: Top 10 at-risk GPUs identified
- ✅ Economic model: Actionable recommendations generated

## Key Findings
1. GPU-A100-001: Health score 45, recommended for sale ($12,000 value)
2. GPU-H100-003: High ECC error rate, predicted failure risk 75%
3. 8 GPUs with thermal issues (>85°C sustained)

## Validated Predictions
- GPU-A100-007: Predicted failure 5 days before actual failure (SUCCESS)
- False positives: 2 GPUs flagged but remained healthy
- False negatives: 0 (no unexpected failures)

## Economic Value
- Avoided failure cost: $X (early detection)
- Optimal sale timing: $Y (3 GPUs sold at 85% of new price)
- Reduced operational cost: $Z (workload rebalancing)

## Recommendations for Full Deployment
1. Scale to full fleet (10,000+ GPUs)
2. Refine prediction models with more failure data
3. Automate workload migration for degraded GPUs
4. Integrate with asset management systems

## ROI Projection
- System cost: $500K/year (10K GPU fleet)
- Expected savings: $3-5M/year
- ROI: 6-10x
```

**Deliverables:**
- Final POC report with results
- Live demo dashboard
- Recommendations for full deployment
- Cost/benefit analysis

---

## POC Success Metrics

### Technical Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Data collection uptime | > 99% | ___ |
| Metric samples collected | 1M+ | ___ |
| Health scores calculated | All 50 GPUs, every 15min | ___ |
| Dashboard latency | < 5 seconds | ___ |

### Business Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Degraded GPUs identified | 3-5 | ___ |
| Predictions validated | 1+ | ___ |
| False positive rate | < 10% | ___ |
| Economic value demonstrated | > $50K | ___ |

---

## Troubleshooting Guide

### Issue: Metrics not flowing to Kafka

**Symptoms:** No data in Kafka topic

**Diagnosis:**
```bash
# Check DCGM exporter on GPU host
curl http://localhost:9400/metrics | grep DCGM

# Check collector logs
journalctl -u gpu-collector -f

# Check Kafka broker
docker exec -it gpu-health-poc-kafka-1 kafka-topics.sh --list --bootstrap-server localhost:9092
```

**Solutions:**
- Restart DCGM exporter
- Check network connectivity
- Verify Kafka broker is reachable

### Issue: Health scores not updating

**Symptoms:** Stale health scores in database

**Diagnosis:**
```bash
# Check health scorer logs
tail -f health_scorer.log

# Check database connection
psql -U gpuhealth -d gpu_assets -c "SELECT NOW()"
```

**Solutions:**
- Restart health scorer service
- Check database connectivity
- Verify stream processor is inserting data

### Issue: High memory usage on monitoring server

**Symptoms:** Server OOM, services crashing

**Diagnosis:**
```bash
docker stats  # Check container memory usage
```

**Solutions:**
- Add memory limits to Docker Compose
- Increase server RAM
- Reduce Kafka retention period
- Archive old TimescaleDB data

---

## Next Steps After POC

1. **Immediate (Week 7-8):**
   - Present POC results to stakeholders
   - Get approval for full deployment
   - Begin procurement for production infrastructure

2. **Short-term (Month 2-3):**
   - Deploy to 500 GPUs (10% of fleet)
   - Refine models with larger dataset
   - Implement automated alerting

3. **Medium-term (Month 4-6):**
   - Full fleet rollout (10,000 GPUs)
   - Production-grade redundancy and failover
   - Integration with asset management

4. **Long-term (Month 6-12):**
   - Advanced predictive models (deep learning)
   - Automated remediation
   - Secondary market integration

---

**Document End**
