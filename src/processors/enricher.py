#!/usr/bin/env python3
"""
Enricher Stream Processor
Enriches validated GPU metrics with asset metadata from PostgreSQL.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
KAFKA_BROKERS = os.getenv('KAFKA_BROKERS', 'kafka:9092').split(',')
KAFKA_INPUT_TOPIC = os.getenv('KAFKA_INPUT_TOPIC', 'gpu-metrics-validated')
KAFKA_OUTPUT_TOPIC = os.getenv('KAFKA_OUTPUT_TOPIC', 'gpu-metrics-enriched')
KAFKA_GROUP_ID = os.getenv('KAFKA_GROUP_ID', 'metric-enricher')
DB_HOST = os.getenv('DB_HOST', 'timescaledb')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'gpu_health')
DB_USER = os.getenv('DB_USER', 'gpu_monitor')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'gpu_monitor_secret')


class MetricEnricher:
    def __init__(self):
        self.consumer = None
        self.producer = None
        self.db_conn = None
        self.asset_cache = {}  # Cache GPU asset metadata
        self.cache_ttl = 300  # 5 minutes
        self.last_cache_refresh = 0
        self.stats = {
            'processed': 0,
            'enriched': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        self.connect_kafka()
        self.connect_database()
    
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
    
    def connect_database(self):
        """Connect to PostgreSQL with retries."""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to database: {DB_HOST}:{DB_PORT}/{DB_NAME} (attempt {attempt+1}/{max_retries})")
                self.db_conn = psycopg2.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    database=DB_NAME,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    cursor_factory=RealDictCursor
                )
                logger.info("Connected to database successfully")
                return
            except psycopg2.Error as e:
                logger.error(f"Database connection failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to database after max retries")
                    raise
    
    def refresh_asset_cache(self):
        """Refresh GPU asset metadata cache from database."""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT 
                    gpu_uuid,
                    model,
                    architecture,
                    compute_capability,
                    memory_gb,
                    hostname,
                    pci_bus_id,
                    rack_id,
                    cluster_id,
                    datacenter,
                    region,
                    purchase_date,
                    deployment_date,
                    warranty_expiry,
                    expected_eol,
                    sla_tier,
                    priority,
                    tags,
                    notes
                FROM gpu_assets
            """)
            
            rows = cursor.fetchall()
            
            # Update cache
            new_cache = {}
            for row in rows:
                gpu_uuid = row['gpu_uuid']
                new_cache[gpu_uuid] = dict(row)
                
                # Convert dates to ISO strings for JSON serialization
                for date_field in ['purchase_date', 'deployment_date', 'warranty_expiry', 'expected_eol']:
                    if row[date_field]:
                        new_cache[gpu_uuid][date_field] = row[date_field].isoformat()
            
            self.asset_cache = new_cache
            self.last_cache_refresh = time.time()
            
            logger.info(f"Refreshed asset cache: {len(self.asset_cache)} GPUs")
            
        except psycopg2.Error as e:
            logger.error(f"Failed to refresh asset cache: {e}")
            # Keep using old cache
    
    def get_asset_metadata(self, gpu_uuid):
        """Get asset metadata for a GPU (from cache or database)."""
        # Refresh cache if needed
        now = time.time()
        if now - self.last_cache_refresh > self.cache_ttl:
            self.refresh_asset_cache()
        
        # Try cache first
        if gpu_uuid in self.asset_cache:
            self.stats['cache_hits'] += 1
            return self.asset_cache[gpu_uuid]
        
        self.stats['cache_misses'] += 1
        
        # Not in cache - query database directly
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT * FROM gpu_assets WHERE gpu_uuid = %s
            """, (gpu_uuid,))
            
            row = cursor.fetchone()
            if row:
                asset = dict(row)
                
                # Convert dates
                for date_field in ['purchase_date', 'deployment_date', 'warranty_expiry', 'expected_eol']:
                    if asset[date_field]:
                        asset[date_field] = asset[date_field].isoformat()
                
                # Add to cache
                self.asset_cache[gpu_uuid] = asset
                
                logger.info(f"Loaded asset metadata for {gpu_uuid} from database")
                return asset
            
        except psycopg2.Error as e:
            logger.error(f"Failed to query asset metadata: {e}")
        
        return None
    
    def enrich_event(self, event):
        """Enrich event with asset metadata."""
        gpu_uuid = event.get('gpu', {}).get('gpu_uuid')
        if not gpu_uuid:
            logger.warning("Event missing gpu_uuid, cannot enrich")
            return event
        
        # Get asset metadata
        asset = self.get_asset_metadata(gpu_uuid)
        
        if asset:
            # Add asset metadata to event
            event['asset'] = {
                'model': asset.get('model'),
                'architecture': asset.get('architecture'),
                'compute_capability': asset.get('compute_capability'),
                'memory_gb': asset.get('memory_gb'),
                'rack_id': asset.get('rack_id'),
                'cluster_id': asset.get('cluster_id'),
                'datacenter': asset.get('datacenter'),
                'region': asset.get('region'),
                'purchase_date': asset.get('purchase_date'),
                'deployment_date': asset.get('deployment_date'),
                'warranty_expiry': asset.get('warranty_expiry'),
                'expected_eol': asset.get('expected_eol'),
                'sla_tier': asset.get('sla_tier'),
                'priority': asset.get('priority'),
                'tags': asset.get('tags'),
                'notes': asset.get('notes')
            }
            
            # Update host info if needed
            if asset.get('hostname') and not event.get('host', {}).get('hostname'):
                event.setdefault('host', {})['hostname'] = asset['hostname']
            
            if asset.get('rack_id') and not event.get('host', {}).get('rack'):
                event.setdefault('host', {})['rack'] = asset['rack_id']
            
            if asset.get('cluster_id') and not event.get('host', {}).get('cluster'):
                event.setdefault('host', {})['cluster'] = asset['cluster_id']
            
            if asset.get('datacenter') and not event.get('host', {}).get('datacenter'):
                event.setdefault('host', {})['datacenter'] = asset['datacenter']
        
        else:
            logger.warning(f"No asset metadata found for GPU {gpu_uuid}")
            event['asset'] = None
        
        # Add enrichment metadata
        event['quality']['enrichment_timestamp'] = datetime.now().isoformat()
        event['quality']['enrichment_version'] = '1.0'
        event['quality']['asset_metadata_found'] = asset is not None
        
        return event
    
    def process_event(self, message):
        """Process a single event."""
        event = message.value
        
        self.stats['processed'] += 1
        
        # Enrich event
        enriched_event = self.enrich_event(event)
        
        # Publish to output topic
        self.producer.send(
            KAFKA_OUTPUT_TOPIC,
            key=message.key,
            value=enriched_event
        )
        
        self.stats['enriched'] += 1
        
        if self.stats['enriched'] % 100 == 0:
            hit_rate = self.stats['cache_hits'] / max(1, self.stats['cache_hits'] + self.stats['cache_misses']) * 100
            logger.info(
                f"Processed {self.stats['processed']} events, "
                f"cache hit rate: {hit_rate:.1f}%"
            )
    
    def log_stats(self):
        """Log processing statistics."""
        hit_rate = self.stats['cache_hits'] / max(1, self.stats['cache_hits'] + self.stats['cache_misses']) * 100
        
        logger.info("=" * 60)
        logger.info("Enrichment Statistics")
        logger.info("=" * 60)
        logger.info(f"Total processed: {self.stats['processed']}")
        logger.info(f"Enriched events: {self.stats['enriched']}")
        logger.info(f"Cache hits:      {self.stats['cache_hits']}")
        logger.info(f"Cache misses:    {self.stats['cache_misses']}")
        logger.info(f"Cache hit rate:  {hit_rate:.1f}%")
        logger.info(f"Cache size:      {len(self.asset_cache)} GPUs")
        logger.info("=" * 60)
    
    def run(self):
        """Main processing loop."""
        logger.info("Starting enricher stream processor")
        logger.info(f"Input topic:  {KAFKA_INPUT_TOPIC}")
        logger.info(f"Output topic: {KAFKA_OUTPUT_TOPIC}")
        
        # Initial cache load
        self.refresh_asset_cache()
        
        last_stats_log = time.time()
        stats_interval = 60
        
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
            logger.info("Shutting down enricher...")
            self.log_stats()
        
        finally:
            # Cleanup
            if self.consumer:
                self.consumer.close()
            if self.producer:
                self.producer.close()
            if self.db_conn:
                self.db_conn.close()
            logger.info("Enricher stopped")


if __name__ == '__main__':
    # Wait for dependencies to be ready
    logger.info("Waiting for services to be ready...")
    time.sleep(15)
    
    enricher = MetricEnricher()
    enricher.run()
