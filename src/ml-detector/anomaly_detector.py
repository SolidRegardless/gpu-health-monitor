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
Real-time Anomaly Detector
Statistical anomaly detection for GPU metrics using z-score and moving averages.
"""

import os
import sys
import time
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DB_HOST = os.getenv('DB_HOST', 'timescaledb')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'gpu_health')
DB_USER = os.getenv('DB_USER', 'gpu_monitor')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'gpu_monitor_secret')
DETECTION_INTERVAL = int(os.getenv('DETECTION_INTERVAL', '300'))  # 5 minutes
Z_SCORE_THRESHOLD = float(os.getenv('Z_SCORE_THRESHOLD', '3.0'))
LOOKBACK_HOURS = int(os.getenv('LOOKBACK_HOURS', '24'))


class AnomalyDetector:
    """Statistical anomaly detector using z-scores and moving statistics."""
    
    def __init__(self):
        self.db_conn = None
        self.connect_database()
    
    def connect_database(self):
        """Connect to database."""
        max_retries = 10
        retry_delay = 5
        
        logger.info("Waiting for database to be ready...")
        time.sleep(20)
        
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
            except Exception as e:
                logger.error(f"Database connection failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    raise
    
    def get_baseline_statistics(self, gpu_uuid: str) -> Dict:
        """Calculate baseline statistics for anomaly detection."""
        cursor = self.db_conn.cursor()
        
        # Get statistics from last 24 hours
        lookback = datetime.now() - timedelta(hours=LOOKBACK_HOURS)
        
        cursor.execute("""
            SELECT
                AVG(gpu_temp) as temp_mean,
                STDDEV(gpu_temp) as temp_std,
                AVG(power_usage) as power_mean,
                STDDEV(power_usage) as power_std,
                AVG(sm_active) as sm_mean,
                STDDEV(sm_active) as sm_std,
                AVG(memory_utilization) as mem_util_mean,
                STDDEV(memory_utilization) as mem_util_std
            FROM gpu_metrics
            WHERE gpu_uuid = %s
              AND time >= %s
        """, (gpu_uuid, lookback))
        
        result = cursor.fetchone()
        return dict(result) if result else {}
    
    def detect_anomalies(self, gpu_uuid: str) -> List[Dict]:
        """Detect anomalies using z-score method."""
        cursor = self.db_conn.cursor()
        
        # Get baseline statistics
        baseline = self.get_baseline_statistics(gpu_uuid)
        if not baseline or baseline['temp_std'] is None:
            logger.warning(f"Insufficient data for baseline statistics for GPU {gpu_uuid}")
            return []
        
        # Get recent metrics (last 5 minutes)
        recent_time = datetime.now() - timedelta(minutes=5)
        cursor.execute("""
            SELECT time, gpu_temp, power_usage, sm_active, memory_utilization
            FROM gpu_metrics
            WHERE gpu_uuid = %s
              AND time >= %s
            ORDER BY time DESC
        """, (gpu_uuid, recent_time))
        
        recent_metrics = cursor.fetchall()
        
        anomalies = []
        for metric in recent_metrics:
            # Calculate z-scores
            temp_z = abs((metric['gpu_temp'] - baseline['temp_mean']) / baseline['temp_std']) if baseline['temp_std'] > 0 else 0
            power_z = abs((metric['power_usage'] - baseline['power_mean']) / baseline['power_std']) if baseline['power_std'] > 0 else 0
            sm_z = abs((metric['sm_active'] - baseline['sm_mean']) / baseline['sm_std']) if baseline['sm_std'] > 0 else 0
            mem_z = abs((metric['memory_utilization'] - baseline['mem_util_mean']) / baseline['mem_util_std']) if baseline['mem_util_std'] > 0 else 0
            
            # Detect anomalies
            if temp_z > Z_SCORE_THRESHOLD:
                anomalies.append({
                    'time': metric['time'],
                    'gpu_uuid': gpu_uuid,
                    'anomaly_type': 'temperature',
                    'value': metric['gpu_temp'],
                    'z_score': round(temp_z, 2),
                    'baseline_mean': round(baseline['temp_mean'], 2),
                    'severity': 'high' if temp_z > 4 else 'medium'
                })
            
            if power_z > Z_SCORE_THRESHOLD:
                anomalies.append({
                    'time': metric['time'],
                    'gpu_uuid': gpu_uuid,
                    'anomaly_type': 'power_usage',
                    'value': metric['power_usage'],
                    'z_score': round(power_z, 2),
                    'baseline_mean': round(baseline['power_mean'], 2),
                    'severity': 'medium' if power_z > 4 else 'low'
                })
            
            if sm_z > Z_SCORE_THRESHOLD:
                anomalies.append({
                    'time': metric['time'],
                    'gpu_uuid': gpu_uuid,
                    'anomaly_type': 'utilization',
                    'value': metric['sm_active'],
                    'z_score': round(sm_z, 2),
                    'baseline_mean': round(baseline['sm_mean'], 2),
                    'severity': 'low'
                })
        
        return anomalies
    
    def save_anomalies(self, anomalies: List[Dict]):
        """Save detected anomalies to database."""
        if not anomalies:
            return
        
        cursor = self.db_conn.cursor()
        
        for anomaly in anomalies:
            cursor.execute("""
                INSERT INTO anomalies (
                    time, gpu_uuid, anomaly_type, value, z_score, 
                    baseline_mean, severity, detected_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT DO NOTHING
            """, (
                anomaly['time'],
                anomaly['gpu_uuid'],
                anomaly['anomaly_type'],
                anomaly['value'],
                anomaly['z_score'],
                anomaly['baseline_mean'],
                anomaly['severity']
            ))
        
        self.db_conn.commit()
        logger.info(f"Saved {len(anomalies)} anomalies to database")
    
    def run(self):
        """Main detection loop."""
        logger.info("Starting Anomaly Detector")
        logger.info(f"Detection interval: {DETECTION_INTERVAL}s")
        logger.info(f"Z-score threshold: {Z_SCORE_THRESHOLD}")
        logger.info(f"Lookback window: {LOOKBACK_HOURS} hours")
        
        while True:
            try:
                logger.info("Starting anomaly detection cycle")
                
                # Get active GPUs
                cursor = self.db_conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT gpu_uuid 
                    FROM gpu_metrics 
                    WHERE time >= NOW() - INTERVAL '1 hour'
                """)
                gpus = cursor.fetchall()
                
                logger.info(f"Detecting anomalies for {len(gpus)} GPUs")
                
                total_anomalies = 0
                for gpu in gpus:
                    gpu_uuid = gpu['gpu_uuid']
                    anomalies = self.detect_anomalies(gpu_uuid)
                    
                    if anomalies:
                        logger.info(f"GPU {gpu_uuid}: {len(anomalies)} anomalies detected")
                        self.save_anomalies(anomalies)
                        total_anomalies += len(anomalies)
                
                logger.info(f"Detection cycle complete: {total_anomalies} total anomalies")
                
            except Exception as e:
                logger.error(f"Error in detection cycle: {e}", exc_info=True)
            
            logger.info(f"Sleeping for {DETECTION_INTERVAL}s")
            time.sleep(DETECTION_INTERVAL)


if __name__ == '__main__':
    detector = AnomalyDetector()
    detector.run()
