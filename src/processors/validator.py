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
Validator Stream Processor
Validates GPU metrics for schema compliance and range checks.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
KAFKA_BROKERS = os.getenv('KAFKA_BROKERS', 'kafka:9092').split(',')
KAFKA_INPUT_TOPIC = os.getenv('KAFKA_INPUT_TOPIC', 'gpu-metrics-raw')
KAFKA_OUTPUT_TOPIC = os.getenv('KAFKA_OUTPUT_TOPIC', 'gpu-metrics-validated')
KAFKA_ERROR_TOPIC = os.getenv('KAFKA_ERROR_TOPIC', 'gpu-metrics-invalid')
KAFKA_GROUP_ID = os.getenv('KAFKA_GROUP_ID', 'metric-validator')


class MetricValidator:
    def __init__(self):
        self.consumer = None
        self.producer = None
        self.stats = {
            'processed': 0,
            'valid': 0,
            'invalid': 0,
            'errors': {}
        }
        self.connect_kafka()
    
    def connect_kafka(self):
        """Connect to Kafka with retries."""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to Kafka: {KAFKA_BROKERS} (attempt {attempt+1}/{max_retries})")
                
                # Consumer
                self.consumer = KafkaConsumer(
                    KAFKA_INPUT_TOPIC,
                    bootstrap_servers=KAFKA_BROKERS,
                    group_id=KAFKA_GROUP_ID,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    auto_offset_reset='earliest',
                    enable_auto_commit=True
                )
                
                # Producer
                self.producer = KafkaProducer(
                    bootstrap_servers=KAFKA_BROKERS,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    compression_type='snappy',
                    acks='all'
                )
                
                logger.info(f"Connected to Kafka successfully")
                return
            except KafkaError as e:
                logger.error(f"Kafka connection failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to Kafka after max retries")
                    raise
    
    def validate_schema(self, event):
        """Validate event schema."""
        errors = []
        
        # Required top-level fields
        required_fields = ['schema_version', 'event_type', 'timestamp', 'gpu', 'host', 'metrics']
        for field in required_fields:
            if field not in event:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return False, errors
        
        # Validate GPU section
        gpu = event.get('gpu', {})
        if not gpu.get('gpu_uuid'):
            errors.append("Missing gpu.gpu_uuid")
        
        # Validate metrics section
        metrics = event.get('metrics', {})
        if not metrics:
            errors.append("Empty metrics object")
        
        required_metric_sections = ['health', 'memory', 'performance', 'clocks']
        for section in required_metric_sections:
            if section not in metrics:
                errors.append(f"Missing metrics.{section}")
        
        return len(errors) == 0, errors
    
    def validate_ranges(self, event):
        """Validate metric values are within acceptable ranges."""
        errors = []
        
        metrics = event.get('metrics', {})
        health = metrics.get('health', {})
        memory = metrics.get('memory', {})
        performance = metrics.get('performance', {})
        
        # Temperature ranges (0-120°C)
        gpu_temp = health.get('gpu_temp_c', 0)
        if not (0 <= gpu_temp <= 120):
            errors.append(f"GPU temperature out of range: {gpu_temp}°C (expected 0-120)")
        
        mem_temp = health.get('memory_temp_c', 0)
        if not (0 <= mem_temp <= 120):
            errors.append(f"Memory temperature out of range: {mem_temp}°C (expected 0-120)")
        
        # Power range (0-800W, allowing for H100)
        power = health.get('power_usage_w', 0)
        if not (0 <= power <= 800):
            errors.append(f"Power usage out of range: {power}W (expected 0-800)")
        
        # Memory ranges
        fb_used = memory.get('fb_used_mib', 0)
        fb_free = memory.get('fb_free_mib', 0)
        
        if fb_used < 0:
            errors.append(f"Negative fb_used_mib: {fb_used}")
        if fb_free < 0:
            errors.append(f"Negative fb_free_mib: {fb_free}")
        
        # Memory utilization (0-100%)
        mem_util = memory.get('utilization_pct', 0)
        if not (0 <= mem_util <= 100):
            errors.append(f"Memory utilization out of range: {mem_util}% (expected 0-100)")
        
        # Performance percentages (0-100%)
        for metric_name, value in performance.items():
            if metric_name.endswith('_pct') or 'active' in metric_name:
                if not (0 <= value <= 100):
                    errors.append(f"{metric_name} out of range: {value}% (expected 0-100)")
        
        # Clock frequencies (should be reasonable)
        clocks = metrics.get('clocks', {})
        sm_clock = clocks.get('sm_clock_mhz', 0)
        if sm_clock > 0 and not (100 <= sm_clock <= 3000):
            errors.append(f"SM clock out of range: {sm_clock} MHz (expected 100-3000)")
        
        return len(errors) == 0, errors
    
    def validate_timestamp(self, event):
        """Validate timestamp is not too old or in the future."""
        errors = []
        
        try:
            timestamp_str = event.get('timestamp')
            if not timestamp_str:
                errors.append("Missing timestamp")
                return False, errors
            
            # Parse timestamp
            if isinstance(timestamp_str, str):
                event_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                errors.append("Timestamp is not a string")
                return False, errors
            
            now = datetime.now(event_time.tzinfo)
            
            # Check if too old (>1 hour)
            age_seconds = (now - event_time).total_seconds()
            if age_seconds > 3600:
                errors.append(f"Event timestamp too old: {age_seconds:.0f}s (>1 hour)")
            
            # Check if in future (allow 5 minutes clock skew)
            if age_seconds < -300:
                errors.append(f"Event timestamp in future: {-age_seconds:.0f}s")
            
        except ValueError as e:
            errors.append(f"Invalid timestamp format: {e}")
        
        return len(errors) == 0, errors
    
    def validate_event(self, event):
        """Run all validations on an event."""
        all_errors = []
        
        # Schema validation
        schema_valid, schema_errors = self.validate_schema(event)
        all_errors.extend(schema_errors)
        
        if not schema_valid:
            # If schema is invalid, skip other validations
            return False, all_errors
        
        # Range validation
        range_valid, range_errors = self.validate_ranges(event)
        all_errors.extend(range_errors)
        
        # Timestamp validation
        time_valid, time_errors = self.validate_timestamp(event)
        all_errors.extend(time_errors)
        
        is_valid = len(all_errors) == 0
        
        # Track error types
        if not is_valid:
            for error in all_errors:
                error_type = error.split(':')[0]
                self.stats['errors'][error_type] = self.stats['errors'].get(error_type, 0) + 1
        
        return is_valid, all_errors
    
    def enrich_validated_event(self, event):
        """Add validation metadata to event."""
        event['quality']['validation_timestamp'] = datetime.now().isoformat()
        event['quality']['validation_version'] = '1.0'
        event['quality']['validation_passed'] = True
        return event
    
    def create_error_event(self, event, errors):
        """Create error event for invalid metrics."""
        return {
            'original_event': event,
            'validation_errors': errors,
            'timestamp': datetime.now().isoformat(),
            'validator_version': '1.0'
        }
    
    def process_event(self, message):
        """Process a single event."""
        event = message.value
        
        self.stats['processed'] += 1
        
        # Validate
        is_valid, errors = self.validate_event(event)
        
        if is_valid:
            # Enrich and publish to validated topic
            validated_event = self.enrich_validated_event(event)
            
            self.producer.send(
                KAFKA_OUTPUT_TOPIC,
                key=message.key,
                value=validated_event
            )
            
            self.stats['valid'] += 1
            
            if self.stats['valid'] % 100 == 0:
                logger.info(f"Processed {self.stats['processed']} events, {self.stats['valid']} valid, {self.stats['invalid']} invalid")
        
        else:
            # Publish to error topic
            error_event = self.create_error_event(event, errors)
            
            self.producer.send(
                KAFKA_ERROR_TOPIC,
                key=message.key,
                value=error_event
            )
            
            self.stats['invalid'] += 1
            
            logger.warning(f"Invalid event from GPU {event.get('gpu', {}).get('gpu_uuid', 'unknown')}: {errors}")
    
    def log_stats(self):
        """Log processing statistics."""
        logger.info("=" * 60)
        logger.info("Validation Statistics")
        logger.info("=" * 60)
        logger.info(f"Total processed: {self.stats['processed']}")
        logger.info(f"Valid events:    {self.stats['valid']} ({self.stats['valid']/max(1, self.stats['processed'])*100:.1f}%)")
        logger.info(f"Invalid events:  {self.stats['invalid']} ({self.stats['invalid']/max(1, self.stats['processed'])*100:.1f}%)")
        
        if self.stats['errors']:
            logger.info("\nError breakdown:")
            for error_type, count in sorted(self.stats['errors'].items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  {error_type}: {count}")
        
        logger.info("=" * 60)
    
    def run(self):
        """Main processing loop."""
        logger.info("Starting validator stream processor")
        logger.info(f"Input topic:  {KAFKA_INPUT_TOPIC}")
        logger.info(f"Output topic: {KAFKA_OUTPUT_TOPIC}")
        logger.info(f"Error topic:  {KAFKA_ERROR_TOPIC}")
        
        last_stats_log = time.time()
        stats_interval = 60  # Log stats every 60 seconds
        
        try:
            for message in self.consumer:
                try:
                    self.process_event(message)
                    
                    # Log stats periodically
                    now = time.time()
                    if now - last_stats_log >= stats_interval:
                        self.log_stats()
                        last_stats_log = now
                
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    continue
        
        except KeyboardInterrupt:
            logger.info("Shutting down validator...")
            self.log_stats()
        
        finally:
            # Cleanup
            if self.consumer:
                self.consumer.close()
            if self.producer:
                self.producer.close()
            logger.info("Validator stopped")


if __name__ == '__main__':
    # Wait for dependencies to be ready
    logger.info("Waiting for services to be ready...")
    time.sleep(10)
    
    validator = MetricValidator()
    validator.run()
