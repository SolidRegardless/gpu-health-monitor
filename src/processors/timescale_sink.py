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
TimescaleDB Sink Processor
Consumes GPU metrics from Kafka and writes to TimescaleDB.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import psycopg2
from psycopg2.extras import execute_values

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
KAFKA_BROKERS = os.getenv('KAFKA_BROKERS', 'kafka:9092').split(',')
KAFKA_INPUT_TOPIC = os.getenv('KAFKA_INPUT_TOPIC', 'gpu-metrics-raw')
KAFKA_GROUP_ID = os.getenv('KAFKA_GROUP_ID', 'timescale-sink')
DB_HOST = os.getenv('DB_HOST', 'timescaledb')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'gpu_health')
DB_USER = os.getenv('DB_USER', 'gpu_monitor')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'gpu_monitor_secret')
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))
BATCH_TIMEOUT = int(os.getenv('BATCH_TIMEOUT', '5'))


class TimescaleSink:
    def __init__(self):
        self.consumer = None
        self.db_conn = None
        self.connect_kafka()
        self.connect_database()
    
    def connect_kafka(self):
        """Connect to Kafka with retries."""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to Kafka: {KAFKA_BROKERS} (attempt {attempt+1}/{max_retries})")
                self.consumer = KafkaConsumer(
                    KAFKA_INPUT_TOPIC,
                    bootstrap_servers=KAFKA_BROKERS,
                    group_id=KAFKA_GROUP_ID,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    auto_offset_reset='earliest',
                    enable_auto_commit=True,
                    max_poll_records=BATCH_SIZE
                )
                logger.info(f"Connected to Kafka successfully, subscribed to {KAFKA_INPUT_TOPIC}")
                return
            except KafkaError as e:
                logger.error(f"Kafka connection failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to Kafka after max retries")
                    raise
    
    def connect_database(self):
        """Connect to TimescaleDB with retries."""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to TimescaleDB: {DB_HOST}:{DB_PORT}/{DB_NAME} (attempt {attempt+1}/{max_retries})")
                self.db_conn = psycopg2.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    database=DB_NAME,
                    user=DB_USER,
                    password=DB_PASSWORD
                )
                self.db_conn.autocommit = False
                logger.info("Connected to TimescaleDB successfully")
                return
            except psycopg2.Error as e:
                logger.error(f"Database connection failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to database after max retries")
                    raise
    
    def parse_event(self, event):
        """Parse Kafka event into database row."""
        try:
            # Extract timestamp
            timestamp = event.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            # Extract GPU info
            gpu = event.get('gpu', {})
            host = event.get('host', {})
            metrics = event.get('metrics', {})
            
            health = metrics.get('health', {})
            memory = metrics.get('memory', {})
            performance = metrics.get('performance', {})
            clocks = metrics.get('clocks', {})
            
            # Build row tuple
            row = (
                timestamp,
                gpu.get('gpu_uuid'),
                host.get('hostname'),
                gpu.get('pci_bus_id'),
                gpu.get('device_index'),
                # Health metrics
                health.get('gpu_temp_c'),
                health.get('memory_temp_c'),
                health.get('power_usage_w'),
                health.get('throttle_reasons'),
                # Memory metrics
                memory.get('fb_used_mib', 0) * 1024 * 1024,  # Convert to bytes
                memory.get('fb_free_mib', 0) * 1024 * 1024,
                memory.get('fb_total_mib', 0) * 1024 * 1024,
                memory.get('utilization_pct'),
                memory.get('ecc_sbe_volatile'),
                memory.get('ecc_dbe_volatile'),
                memory.get('ecc_sbe_aggregate'),
                memory.get('ecc_dbe_aggregate'),
                memory.get('retired_pages_sbe'),
                memory.get('retired_pages_dbe'),
                # Performance metrics
                performance.get('sm_active_pct'),
                performance.get('sm_occupancy_pct'),
                performance.get('tensor_active_pct'),
                performance.get('dram_active_pct'),
                performance.get('pcie_tx_mb_per_sec', 0) * 1024 * 1024,  # Convert to bytes/sec
                performance.get('pcie_rx_mb_per_sec', 0) * 1024 * 1024,
                # Clock metrics
                clocks.get('sm_clock_mhz'),
                clocks.get('mem_clock_mhz'),
                # Utilization (duplicate sm_active for now)
                performance.get('sm_active_pct'),
                performance.get('dram_active_pct', 0) * 0.8,  # Approximate
                # Quality
                event.get('quality', {}).get('collection_latency_ms', 0),
                True  # validation_passed
            )
            
            return row
            
        except Exception as e:
            logger.error(f"Failed to parse event: {e}")
            logger.debug(f"Event: {json.dumps(event, indent=2)}")
            return None
    
    def write_batch(self, rows):
        """Write batch of rows to TimescaleDB."""
        if not rows:
            return
        
        try:
            cursor = self.db_conn.cursor()
            
            execute_values(
                cursor,
                """
                INSERT INTO gpu_metrics (
                    time, gpu_uuid, hostname, pci_bus_id, device_index,
                    gpu_temp, memory_temp, power_usage, throttle_reasons,
                    fb_used_bytes, fb_free_bytes, fb_total_bytes, memory_utilization,
                    ecc_sbe_volatile, ecc_dbe_volatile, ecc_sbe_aggregate, ecc_dbe_aggregate,
                    retired_pages_sbe, retired_pages_dbe,
                    sm_active, sm_occupancy, tensor_active, dram_active,
                    pcie_tx_bytes_per_sec, pcie_rx_bytes_per_sec,
                    sm_clock_mhz, mem_clock_mhz,
                    gpu_utilization, mem_copy_utilization,
                    collection_latency_ms, validation_passed
                ) VALUES %s
                ON CONFLICT (time, gpu_uuid) DO NOTHING
                """,
                rows,
                page_size=100
            )
            
            self.db_conn.commit()
            logger.info(f"Wrote {len(rows)} metrics to TimescaleDB")
            
        except psycopg2.Error as e:
            logger.error(f"Database write failed: {e}")
            self.db_conn.rollback()
            
            # Try to reconnect
            try:
                self.db_conn.close()
            except:
                pass
            self.connect_database()
    
    def run(self):
        """Main processing loop."""
        logger.info("Starting TimescaleDB sink processor")
        logger.info(f"Kafka topic: {KAFKA_INPUT_TOPIC}")
        logger.info(f"Batch size: {BATCH_SIZE}")
        logger.info(f"Batch timeout: {BATCH_TIMEOUT}s")
        
        batch = []
        last_write = time.time()
        
        try:
            for message in self.consumer:
                try:
                    event = message.value
                    
                    # Parse event
                    row = self.parse_event(event)
                    if row:
                        batch.append(row)
                    
                    # Write batch if size or timeout reached
                    now = time.time()
                    if len(batch) >= BATCH_SIZE or (batch and now - last_write >= BATCH_TIMEOUT):
                        self.write_batch(batch)
                        batch = []
                        last_write = now
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    continue
        
        except KeyboardInterrupt:
            logger.info("Shutting down sink processor...")
            
            # Write any remaining batch
            if batch:
                self.write_batch(batch)
        
        finally:
            # Cleanup
            if self.consumer:
                self.consumer.close()
            if self.db_conn:
                self.db_conn.close()
            logger.info("Sink processor stopped")


if __name__ == '__main__':
    # Wait for dependencies to be ready
    logger.info("Waiting for services to be ready...")
    time.sleep(15)
    
    sink = TimescaleSink()
    sink.run()
