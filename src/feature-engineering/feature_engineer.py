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
Feature Engineering Service
Computes ML features from raw GPU metrics for training and inference.
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from scipy import stats

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
FEATURE_INTERVAL = int(os.getenv('FEATURE_INTERVAL', '3600'))  # 1 hour


class GPUFeatureEngineer:
    """Extract and compute ML features from GPU metrics."""
    
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
    
    def query_metrics(self, gpu_uuid: str, lookback_days: int = 7) -> pd.DataFrame:
        """Query raw metrics for a GPU."""
        cursor = self.db_conn.cursor()
        
        lookback = datetime.now() - timedelta(days=lookback_days)
        
        cursor.execute("""
            SELECT
                time,
                gpu_temp,
                memory_temp,
                power_usage,
                throttle_reasons,
                sm_active,
                sm_occupancy,
                tensor_active,
                memory_utilization,
                ecc_sbe_volatile,
                ecc_dbe_volatile,
                gpu_utilization
            FROM gpu_metrics
            WHERE gpu_uuid = %s
              AND time >= %s
            ORDER BY time ASC
        """, (gpu_uuid, lookback))
        
        rows = cursor.fetchall()
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    
    def query_asset_metadata(self, gpu_uuid: str) -> dict:
        """Query asset metadata."""
        cursor = self.db_conn.cursor()
        
        cursor.execute("""
            SELECT
                model,
                deployment_date,
                warranty_expiry,
                tags
            FROM gpu_assets
            WHERE gpu_uuid = %s
        """, (gpu_uuid,))
        
        row = cursor.fetchone()
        return dict(row) if row else {}
    
    def extract_features(self, gpu_uuid: str, lookback_days: int = 7) -> dict:
        """
        Extract all features for a GPU.
        
        Returns:
            Dictionary of feature_name: value
        """
        logger.info(f"Extracting features for GPU {gpu_uuid}")
        
        # Query data
        metrics = self.query_metrics(gpu_uuid, lookback_days)
        asset = self.query_asset_metadata(gpu_uuid)
        
        if metrics.empty:
            logger.warning(f"No metrics found for GPU {gpu_uuid}")
            return {}
        
        features = {}
        
        # Statistical features
        features.update(self._statistical_features(metrics))
        
        # Event count features
        features.update(self._event_features(metrics))
        
        # Anomaly features
        features.update(self._anomaly_features(metrics))
        
        # Metadata features
        features.update(self._metadata_features(asset))
        
        logger.info(f"Extracted {len(features)} features for GPU {gpu_uuid}")
        
        return features
    
    def _statistical_features(self, metrics: pd.DataFrame) -> dict:
        """Compute statistical features from time-series."""
        features = {}
        
        # Temperature features
        features['gpu_temp_mean'] = metrics['gpu_temp'].mean()
        features['gpu_temp_std'] = metrics['gpu_temp'].std()
        features['gpu_temp_min'] = metrics['gpu_temp'].min()
        features['gpu_temp_max'] = metrics['gpu_temp'].max()
        
        # Linear trend (slope)
        if len(metrics) > 2:
            x = np.arange(len(metrics))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, metrics['gpu_temp'])
            features['gpu_temp_trend'] = slope
        else:
            features['gpu_temp_trend'] = 0.0
        
        # Power features
        features['power_usage_mean'] = metrics['power_usage'].mean()
        features['power_usage_std'] = metrics['power_usage'].std()
        
        # Coefficient of variation
        if features['power_usage_mean'] > 0:
            features['power_usage_cv'] = features['power_usage_std'] / features['power_usage_mean']
        else:
            features['power_usage_cv'] = 0.0
        
        # Performance per watt
        mean_sm = metrics['sm_active'].mean()
        if features['power_usage_mean'] > 0:
            features['power_efficiency'] = mean_sm / features['power_usage_mean']
        else:
            features['power_efficiency'] = 0.0
        
        # SM features
        features['sm_active_mean'] = metrics['sm_active'].mean()
        features['sm_active_std'] = metrics['sm_active'].std()
        features['sm_occupancy_mean'] = metrics['sm_occupancy'].mean() if 'sm_occupancy' in metrics else 0.0
        
        # Memory features
        features['memory_util_mean'] = metrics['memory_utilization'].mean()
        features['memory_util_std'] = metrics['memory_utilization'].std()
        
        return features
    
    def _event_features(self, metrics: pd.DataFrame) -> dict:
        """Count specific events."""
        features = {}
        
        # Throttle reason breakdown (bit flags)
        features['thermal_throttle_count'] = ((metrics['throttle_reasons'] & (1 << 6)) > 0).sum()
        features['power_brake_count'] = ((metrics['throttle_reasons'] & (1 << 7)) > 0).sum()
        features['sw_power_cap_count'] = ((metrics['throttle_reasons'] & (1 << 2)) > 0).sum()
        
        # ECC error events
        features['ecc_sbe_event_count'] = (metrics['ecc_sbe_volatile'] > 0).sum()
        features['ecc_dbe_event_count'] = (metrics['ecc_dbe_volatile'] > 0).sum()
        
        return features
    
    def _anomaly_features(self, metrics: pd.DataFrame) -> dict:
        """Detect anomalies and count them."""
        features = {}
        
        # Temperature spikes (> mean + 2*std)
        temp_mean = metrics['gpu_temp'].mean()
        temp_std = metrics['gpu_temp'].std()
        
        if temp_std > 0:
            features['temp_spike_count'] = ((metrics['gpu_temp'] > temp_mean + 2 * temp_std) |
                                            (metrics['gpu_temp'] < temp_mean - 2 * temp_std)).sum()
        else:
            features['temp_spike_count'] = 0
        
        # Power anomalies
        power_mean = metrics['power_usage'].mean()
        power_std = metrics['power_usage'].std()
        
        if power_std > 0:
            features['power_anomaly_count'] = ((metrics['power_usage'] > power_mean + 2 * power_std) |
                                                (metrics['power_usage'] < power_mean - 2 * power_std)).sum()
        else:
            features['power_anomaly_count'] = 0
        
        # Throttle duration (approximate hours)
        # Assuming 10s sampling interval
        throttle_events = (metrics['throttle_reasons'] > 0).sum()
        features['throttle_duration_hours'] = (throttle_events * 10) / 3600.0
        
        return features
    
    def _metadata_features(self, asset: dict) -> dict:
        """Extract features from asset metadata."""
        features = {}
        
        if asset:
            # GPU age (days since deployment)
            if 'deployment_date' in asset and asset['deployment_date']:
                deployment_date = pd.to_datetime(asset['deployment_date'])
                age_days = (pd.Timestamp.now() - deployment_date).days
                features['gpu_age_days'] = age_days
            else:
                features['gpu_age_days'] = 0
            
            # Warranty remaining (days)
            if 'warranty_expiry' in asset and asset['warranty_expiry']:
                warranty_expiry = pd.to_datetime(asset['warranty_expiry'])
                warranty_days = (warranty_expiry - pd.Timestamp.now()).days
                features['warranty_remaining_days'] = warranty_days
            else:
                features['warranty_remaining_days'] = 0
            
            # Model encoding (one-hot)
            model = asset.get('model', '')
            features['model_a100'] = 'A100' in model
            features['model_h100'] = 'H100' in model
        else:
            features['gpu_age_days'] = 0
            features['warranty_remaining_days'] = 0
            features['model_a100'] = False
            features['model_h100'] = False
        
        # Total operating hours (rough estimate from deployment)
        if features['gpu_age_days'] > 0:
            features['total_operating_hours'] = features['gpu_age_days'] * 24.0
        else:
            features['total_operating_hours'] = 0.0
        
        return features
    
    def save_features(self, gpu_uuid: str, features: dict):
        """Save computed features to feature store."""
        cursor = self.db_conn.cursor()
        
        # Convert numpy types to Python types
        cleaned_features = {}
        for key, value in features.items():
            if isinstance(value, (np.integer, np.floating)):
                cleaned_features[key] = float(value) if isinstance(value, np.floating) else int(value)
            elif isinstance(value, (np.bool_)):
                cleaned_features[key] = bool(value)
            else:
                cleaned_features[key] = value
        
        # Build column list dynamically
        columns = ['time', 'gpu_uuid'] + list(cleaned_features.keys())
        values = [datetime.now(), gpu_uuid] + list(cleaned_features.values())
        
        placeholders = ', '.join(['%s'] * len(values))
        columns_str = ', '.join(columns)
        
        cursor.execute(f"""
            INSERT INTO gpu_features ({columns_str})
            VALUES ({placeholders})
            ON CONFLICT (time, gpu_uuid) DO UPDATE SET
                computed_at = NOW()
        """, values)
        
        self.db_conn.commit()
        logger.info(f"Saved {len(cleaned_features)} features for GPU {gpu_uuid}")
    
    def run(self):
        """Main feature engineering loop."""
        logger.info("Starting Feature Engineering Service")
        logger.info(f"Feature computation interval: {FEATURE_INTERVAL}s")
        
        while True:
            try:
                logger.info("Starting feature extraction cycle")
                
                # Get list of active GPUs
                cursor = self.db_conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT gpu_uuid
                    FROM gpu_metrics
                    WHERE time >= NOW() - INTERVAL '7 days'
                """)
                gpus = cursor.fetchall()
                
                logger.info(f"Extracting features for {len(gpus)} GPUs")
                
                for gpu in gpus:
                    gpu_uuid = gpu['gpu_uuid']
                    
                    try:
                        features = self.extract_features(gpu_uuid, lookback_days=7)
                        
                        if features:
                            self.save_features(gpu_uuid, features)
                    except Exception as e:
                        logger.error(f"Error processing GPU {gpu_uuid}: {e}", exc_info=True)
                
                logger.info(f"Feature extraction cycle complete")
                
            except Exception as e:
                logger.error(f"Error in feature extraction cycle: {e}", exc_info=True)
            
            logger.info(f"Sleeping for {FEATURE_INTERVAL}s")
            time.sleep(FEATURE_INTERVAL)


if __name__ == '__main__':
    engineer = GPUFeatureEngineer()
    engineer.run()
