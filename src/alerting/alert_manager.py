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
Alert Manager
Monitors health scores and anomalies, generates alerts.
"""

import os
import time
import logging
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_HOST = os.getenv('DB_HOST', 'timescaledb')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'gpu_health')
DB_USER = os.getenv('DB_USER', 'gpu_monitor')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'gpu_monitor_secret')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))  # 1 minute


class AlertManager:
    def __init__(self):
        self.db_conn = None
        self.connect_database()
    
    def connect_database(self):
        logger.info("Waiting for database...")
        time.sleep(20)
        
        self.db_conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        logger.info("Connected to database")
    
    def check_health_scores(self):
        """Alert on critically low health scores."""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT gpu_uuid, overall_score, health_grade, time
            FROM gpu_health_scores
            WHERE time >= NOW() - INTERVAL '30 minutes'
              AND overall_score < 50
            ORDER BY time DESC
            LIMIT 10
        """)
        
        for row in cursor.fetchall():
            logger.warning(f"🚨 HEALTH ALERT: GPU {row['gpu_uuid']} health score {row['overall_score']} ({row['health_grade']}) at {row['time']}")
    
    def check_anomalies(self):
        """Alert on new high-severity anomalies."""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT gpu_uuid, anomaly_type, value, z_score, severity, time
            FROM anomalies
            WHERE detected_at >= NOW() - INTERVAL '10 minutes'
              AND severity = 'high'
              AND NOT acknowledged
            ORDER BY time DESC
            LIMIT 10
        """)
        
        for row in cursor.fetchall():
            logger.warning(f"⚠️ ANOMALY ALERT: GPU {row['gpu_uuid']} {row['anomaly_type']} = {row['value']} (z-score: {row['z_score']}, severity: {row['severity']}) at {row['time']}")
    
    def run(self):
        logger.info("Starting Alert Manager")
        logger.info(f"Check interval: {CHECK_INTERVAL}s")
        
        while True:
            try:
                self.check_health_scores()
                self.check_anomalies()
            except Exception as e:
                logger.error(f"Error in alert cycle: {e}", exc_info=True)
            
            time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    manager = AlertManager()
    manager.run()
