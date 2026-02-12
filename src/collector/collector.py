#!/usr/bin/env python3
# MIT License
# Copyright (c) 2026 Stuart Hart <stuarthart@msn.com>
#
# GPU Health Monitor - Production-grade GPU monitoring and predictive maintenance
# https://github.com/stuarthart/gpu-health-monitor
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""
GPU Metrics Collector
Scrapes DCGM exporter and publishes to Kafka.
"""

import os
import sys
import time
import json
import requests
import logging
from datetime import datetime, timezone
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DCGM_ENDPOINT = os.getenv('DCGM_ENDPOINT', 'http://mock-dcgm:9400/metrics')
KAFKA_BROKERS = os.getenv('KAFKA_BROKERS', 'kafka:9092').split(',')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'gpu-metrics-raw')
COLLECTION_INTERVAL = int(os.getenv('COLLECTION_INTERVAL', '10'))
CLUSTER_NAME = os.getenv('CLUSTER_NAME', 'local-development')
DATACENTER = os.getenv('DATACENTER', 'local')
RACK_ID = os.getenv('RACK_ID', 'rack-01')


class DCGMCollector:
    def __init__(self):
        self.hostname = os.getenv('HOSTNAME', 'collector-host')
        self.producer = None
        self.connect_kafka()
    
    def connect_kafka(self):
        """Connect to Kafka with retries."""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to Kafka: {KAFKA_BROKERS} (attempt {attempt+1}/{max_retries})")
                self.producer = KafkaProducer(
                    bootstrap_servers=KAFKA_BROKERS,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    compression_type=None,
                    acks='all',  # Wait for all replicas
                    retries=3,
                    max_in_flight_requests_per_connection=5
                )
                logger.info("Connected to Kafka successfully")
                return
            except KafkaError as e:
                logger.error(f"Kafka connection failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to Kafka after max retries")
                    raise
    
    def parse_prometheus_metrics(self, text):
        """Parse Prometheus format metrics from DCGM exporter."""
        metrics = {}
        gpu_uuid = None
        gpu_model = None
        
        for line in text.split('\n'):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse metric line: metric_name{labels} value [timestamp]
            try:
                # Extract metric name and labels
                if '{' in line:
                    metric_name = line.split('{')[0]
                    labels_and_rest = line.split('{', 1)[1]
                    labels_str = labels_and_rest.split('}')[0]
                    value_parts = labels_and_rest.split('}', 1)[1].strip().split()
                    
                    # Parse labels
                    labels = {}
                    for label_pair in labels_str.split(','):
                        if '=' in label_pair:
                            key, val = label_pair.split('=', 1)
                            labels[key.strip()] = val.strip(' "')
                    
                    # Extract GPU UUID and model
                    if 'UUID' in labels:
                        gpu_uuid = labels['UUID']
                    if 'modelName' in labels:
                        gpu_model = labels['modelName']
                    
                    # Extract value
                    value = float(value_parts[0])
                    
                    # Store metric
                    metrics[metric_name] = value
                    
            except Exception as e:
                logger.warning(f"Failed to parse line: {line} - {e}")
                continue
        
        return metrics, gpu_uuid, gpu_model
    
    def build_metric_event(self, metrics, gpu_uuid, gpu_model):
        """Build metric event in the format expected by the pipeline."""
        collection_time = datetime.now(timezone.utc)
        
        event = {
            'schema_version': '1.0',
            'event_type': 'gpu_metric_sample',
            'timestamp': collection_time.isoformat(),
            'collection_timestamp': collection_time.isoformat(),
            'processing_timestamp': collection_time.isoformat(),
            
            'gpu': {
                'gpu_id': gpu_uuid.split('-')[1] if gpu_uuid else 'unknown',
                'gpu_uuid': gpu_uuid or 'unknown',
                'device_index': 0,
                'pci_bus_id': '0000:3B:00.0',  # Mock value
                'name': gpu_model or 'Unknown GPU',
                'architecture': 'Ampere' if 'A100' in (gpu_model or '') else 'Unknown',
                'compute_capability': '8.0' if 'A100' in (gpu_model or '') else '0.0'
            },
            
            'host': {
                'hostname': self.hostname,
                'cluster': CLUSTER_NAME,
                'rack': RACK_ID,
                'datacenter': DATACENTER
            },
            
            'metrics': {
                'health': {
                    'gpu_temp_c': metrics.get('DCGM_FI_DEV_GPU_TEMP', 0),
                    'memory_temp_c': metrics.get('DCGM_FI_DEV_MEMORY_TEMP', 0),
                    'power_usage_w': metrics.get('DCGM_FI_DEV_POWER_USAGE', 0),
                    'throttle_reasons': int(metrics.get('DCGM_FI_DEV_CLOCK_THROTTLE_REASONS', 0)),
                    'throttle_reasons_decoded': self.decode_throttle_reasons(
                        int(metrics.get('DCGM_FI_DEV_CLOCK_THROTTLE_REASONS', 0))
                    )
                },
                
                'memory': {
                    'fb_used_mib': int(metrics.get('DCGM_FI_DEV_FB_USED', 0)),
                    'fb_free_mib': int(metrics.get('DCGM_FI_DEV_FB_FREE', 0)),
                    'fb_total_mib': int(metrics.get('DCGM_FI_DEV_FB_USED', 0) + metrics.get('DCGM_FI_DEV_FB_FREE', 0)),
                    'utilization_pct': self.calculate_memory_util(metrics),
                    'ecc_sbe_volatile': int(metrics.get('DCGM_FI_DEV_ECC_SBE_VOL_TOTAL', 0)),
                    'ecc_dbe_volatile': int(metrics.get('DCGM_FI_DEV_ECC_DBE_VOL_TOTAL', 0)),
                    'ecc_sbe_aggregate': int(metrics.get('DCGM_FI_DEV_ECC_SBE_AGG_TOTAL', 0)),
                    'ecc_dbe_aggregate': int(metrics.get('DCGM_FI_DEV_ECC_DBE_AGG_TOTAL', 0)),
                    'retired_pages_sbe': int(metrics.get('DCGM_FI_DEV_RETIRED_SBE', 0)),
                    'retired_pages_dbe': int(metrics.get('DCGM_FI_DEV_RETIRED_DBE', 0))
                },
                
                'performance': {
                    'sm_active_pct': metrics.get('DCGM_FI_PROF_SM_ACTIVE', 0),
                    'sm_occupancy_pct': metrics.get('DCGM_FI_PROF_SM_OCCUPANCY', 0),
                    'tensor_active_pct': metrics.get('DCGM_FI_PROF_PIPE_TENSOR_ACTIVE', 0),
                    'dram_active_pct': metrics.get('DCGM_FI_PROF_DRAM_ACTIVE', 0),
                    'pcie_tx_mb_per_sec': metrics.get('DCGM_FI_PROF_PCIE_TX_BYTES', 0) / (1024 * 1024),
                    'pcie_rx_mb_per_sec': metrics.get('DCGM_FI_PROF_PCIE_RX_BYTES', 0) / (1024 * 1024)
                },
                
                'clocks': {
                    'sm_clock_mhz': int(metrics.get('DCGM_FI_DEV_SM_CLOCK', 0)),
                    'mem_clock_mhz': int(metrics.get('DCGM_FI_DEV_MEM_CLOCK', 0))
                }
            },
            
            'quality': {
                'collection_latency_ms': 0,  # Will be calculated in processor
                'stale': False,
                'sample_count': 1,
                'error': None
            }
        }
        
        return event
    
    @staticmethod
    def decode_throttle_reasons(bitmask):
        """Decode throttle reasons bitmask into list of reasons."""
        reasons = []
        
        if bitmask & (1 << 3):
            reasons.append('HW_SLOWDOWN')
        if bitmask & (1 << 6):
            reasons.append('HW_THERMAL')
        if bitmask & (1 << 7):
            reasons.append('HW_POWER_BRAKE')
        if bitmask & (1 << 2):
            reasons.append('SW_POWER_CAP')
        if bitmask & (1 << 5):
            reasons.append('SW_THERMAL')
        
        return reasons
    
    @staticmethod
    def calculate_memory_util(metrics):
        """Calculate memory utilization percentage."""
        used = metrics.get('DCGM_FI_DEV_FB_USED', 0)
        free = metrics.get('DCGM_FI_DEV_FB_FREE', 0)
        total = used + free
        
        if total == 0:
            return 0.0
        
        return (used / total) * 100.0
    
    def collect_and_publish(self):
        """Collect metrics from DCGM and publish to Kafka."""
        try:
            # Scrape DCGM exporter
            logger.debug(f"Scraping metrics from {DCGM_ENDPOINT}")
            response = requests.get(DCGM_ENDPOINT, timeout=5)
            response.raise_for_status()
            
            # Parse metrics
            metrics, gpu_uuid, gpu_model = self.parse_prometheus_metrics(response.text)
            
            if not metrics:
                logger.warning("No metrics parsed from DCGM exporter")
                return
            
            # Build event
            event = self.build_metric_event(metrics, gpu_uuid, gpu_model)
            
            # Publish to Kafka
            future = self.producer.send(
                KAFKA_TOPIC,
                key=gpu_uuid.encode('utf-8') if gpu_uuid else b'unknown',
                value=event
            )
            
            # Wait for send confirmation
            record_metadata = future.get(timeout=10)
            
            logger.info(
                f"Published metrics for GPU {gpu_uuid} to {record_metadata.topic} "
                f"partition {record_metadata.partition} offset {record_metadata.offset}"
            )
            
        except requests.RequestException as e:
            logger.error(f"Failed to scrape DCGM endpoint: {e}")
        except KafkaError as e:
            logger.error(f"Failed to publish to Kafka: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
    
    def run(self):
        """Main collection loop."""
        logger.info(f"Starting GPU metrics collector")
        logger.info(f"DCGM Endpoint: {DCGM_ENDPOINT}")
        logger.info(f"Kafka Topic: {KAFKA_TOPIC}")
        logger.info(f"Collection Interval: {COLLECTION_INTERVAL}s")
        
        while True:
            try:
                self.collect_and_publish()
                time.sleep(COLLECTION_INTERVAL)
            except KeyboardInterrupt:
                logger.info("Shutting down collector...")
                break
            except Exception as e:
                logger.error(f"Error in collection loop: {e}", exc_info=True)
                time.sleep(COLLECTION_INTERVAL)
        
        # Cleanup
        if self.producer:
            self.producer.close()
        logger.info("Collector stopped")


if __name__ == '__main__':
    # Wait for dependencies to be ready
    logger.info("Waiting for services to be ready...")
    time.sleep(10)
    
    collector = DCGMCollector()
    collector.run()
