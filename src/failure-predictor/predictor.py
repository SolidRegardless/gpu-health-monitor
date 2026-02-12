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
GPU Failure Predictor Service
XGBoost-based failure probability prediction.
"""

import os
import sys
import time
import logging
import json
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import joblib

# ML libraries
try:
    import xgboost as xgb
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score, precision_recall_curve
except ImportError:
    xgb = None
    logger.warning("XGBoost not available, using heuristic predictions")

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
PREDICTION_INTERVAL = int(os.getenv('PREDICTION_INTERVAL', '3600'))  # 1 hour
MODEL_PATH = os.getenv('MODEL_PATH', '/models/failure_predictor.pkl')


class FailurePredictor:
    """XGBoost-based GPU failure predictor."""
    
    def __init__(self):
        self.db_conn = None
        self.model = None
        self.feature_names = None
        self.connect_database()
        self.load_or_train_model()
    
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
    
    def load_or_train_model(self):
        """Load existing model or train a new one."""
        if os.path.exists(MODEL_PATH):
            logger.info(f"Loading model from {MODEL_PATH}")
            try:
                model_data = joblib.load(MODEL_PATH)
                self.model = model_data['model']
                self.feature_names = model_data['feature_names']
                logger.info(f"Loaded model with {len(self.feature_names)} features")
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                self.train_initial_model()
        else:
            logger.info("No existing model found, training initial model")
            self.train_initial_model()
    
    def train_initial_model(self):
        """Train initial model on synthetic failure data."""
        logger.info("Training initial failure prediction model")
        
        if xgb is None:
            logger.warning("XGBoost not available, using heuristic model")
            self.model = None
            return
        
        # Generate synthetic training data
        logger.info("Generating synthetic training data...")
        X_train, y_train = self.generate_synthetic_data(n_samples=1000)
        
        if X_train is None:
            logger.error("Failed to generate training data")
            return
        
        self.feature_names = X_train.columns.tolist()
        
        # Train model
        logger.info(f"Training XGBoost model with {len(self.feature_names)} features")
        
        # Calculate class weight for imbalanced data
        failure_rate = y_train.mean()
        scale_pos_weight = (1 - failure_rate) / failure_rate if failure_rate > 0 else 1.0
        
        self.model = xgb.XGBClassifier(
            objective='binary:logistic',
            eval_metric='auc',
            max_depth=5,
            learning_rate=0.1,
            n_estimators=100,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            random_state=42
        )
        
        self.model.fit(X_train, y_train)
        
        # Evaluate
        train_preds = self.model.predict_proba(X_train)[:, 1]
        auc = roc_auc_score(y_train, train_preds)
        logger.info(f"Training AUC: {auc:.4f}")
        
        # Save model
        self.save_model()
        
        logger.info("Initial model training complete")
    
    def generate_synthetic_data(self, n_samples: int = 1000):
        """Generate synthetic failure training data."""
        try:
            # Query recent features
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT *
                FROM gpu_features
                ORDER BY time DESC
                LIMIT 100
            """)
            
            rows = cursor.fetchall()
            
            if not rows:
                logger.warning("No features available, generating from scratch")
                # Create synthetic features
                np.random.seed(42)
                
                X = pd.DataFrame({
                    'gpu_temp_mean': np.random.normal(73, 5, n_samples),
                    'gpu_temp_std': np.random.gamma(2, 2, n_samples),
                    'gpu_temp_trend': np.random.normal(0, 0.1, n_samples),
                    'power_usage_mean': np.random.normal(350, 30, n_samples),
                    'power_usage_cv': np.random.gamma(1, 0.05, n_samples),
                    'thermal_throttle_count': np.random.poisson(5, n_samples),
                    'ecc_dbe_event_count': np.random.poisson(0.1, n_samples),
                    'temp_spike_count': np.random.poisson(2, n_samples),
                    'gpu_age_days': np.random.randint(0, 1000, n_samples),
                })
                
                # Generate labels based on heuristics
                # Higher temp, more throttling, more errors -> higher failure risk
                failure_score = (
                    (X['gpu_temp_mean'] > 80) * 0.3 +
                    (X['thermal_throttle_count'] > 10) * 0.3 +
                    (X['ecc_dbe_event_count'] > 0) * 0.4 +
                    (X['gpu_age_days'] > 730) * 0.2
                )
                
                # Convert to binary labels (30% failure rate)
                y = (failure_score + np.random.normal(0, 0.2, n_samples)) > 0.6
                
                return X, y.astype(int)
            else:
                # Use real features and generate synthetic labels
                df = pd.DataFrame(rows)
                
                # Drop non-feature columns
                feature_cols = [col for col in df.columns if col not in ['time', 'gpu_uuid', 'feature_version', 'computed_at']]
                X = df[feature_cols].copy()
                
                # Fill NaN
                X = X.fillna(0)
                
                # Generate synthetic labels
                failure_score = (
                    (X['gpu_temp_mean'] > 80).astype(float) * 0.3 +
                    (X['thermal_throttle_count'] > 10).astype(float) * 0.3 +
                    (X['ecc_dbe_event_count'] > 0).astype(float) * 0.4
                )
                
                y = (failure_score > 0.5).astype(int)
                
                # Duplicate data if needed
                if len(X) < n_samples:
                    repeat_times = n_samples // len(X) + 1
                    X = pd.concat([X] * repeat_times, ignore_index=True)[:n_samples]
                    y = np.tile(y, repeat_times)[:n_samples]
                
                return X, y
        
        except Exception as e:
            logger.error(f"Error generating synthetic data: {e}", exc_info=True)
            return None, None
    
    def save_model(self):
        """Save model to disk."""
        try:
            os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
            
            model_data = {
                'model': self.model,
                'feature_names': self.feature_names,
                'trained_at': datetime.now().isoformat()
            }
            
            joblib.dump(model_data, MODEL_PATH)
            logger.info(f"Model saved to {MODEL_PATH}")
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def predict_failure(self, gpu_uuid: str) -> dict:
        """Predict failure probability for a GPU."""
        try:
            # Get latest features
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT *
                FROM gpu_features
                WHERE gpu_uuid = %s
                ORDER BY time DESC
                LIMIT 1
            """, (gpu_uuid,))
            
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"No features found for GPU {gpu_uuid}")
                return None
            
            # Extract features
            features_dict = dict(row)
            feature_cols = [col for col in features_dict.keys() if col not in ['time', 'gpu_uuid', 'feature_version', 'computed_at']]
            
            # Create feature vector
            if self.model and self.feature_names:
                # Use trained model
                X = pd.DataFrame([features_dict])[self.feature_names]
                X = X.fillna(0)
                
                failure_prob_30d = float(self.model.predict_proba(X)[0, 1])
            else:
                # Use heuristic model
                failure_prob_30d = self.heuristic_prediction(features_dict)
            
            # Scale to different time horizons
            failure_prob_7d = failure_prob_30d * 0.25
            failure_prob_90d = min(failure_prob_30d * 2.5, 0.99)
            
            # Estimate time to failure (inverse of probability)
            if failure_prob_30d > 0.1:
                estimated_ttf_days = int(30 / failure_prob_30d)
            else:
                estimated_ttf_days = 365
            
            # Predict failure type (heuristic)
            failure_type = self.predict_failure_type(features_dict)
            
            return {
                'gpu_uuid': gpu_uuid,
                'failure_prob_7d': round(failure_prob_7d, 4),
                'failure_prob_30d': round(failure_prob_30d, 4),
                'failure_prob_90d': round(failure_prob_90d, 4),
                'predicted_failure_type': failure_type,
                'estimated_ttf_days': estimated_ttf_days,
                'model_name': 'xgb_v1' if self.model else 'heuristic',
                'model_version': '1.0',
                'confidence': 0.75 if self.model else 0.60
            }
        
        except Exception as e:
            logger.error(f"Error predicting failure for {gpu_uuid}: {e}", exc_info=True)
            return None
    
    def heuristic_prediction(self, features: dict) -> float:
        """Simple heuristic-based failure prediction."""
        score = 0.0
        
        # Temperature risk
        temp_mean = features.get('gpu_temp_mean', 70)
        if temp_mean > 85:
            score += 0.4
        elif temp_mean > 80:
            score += 0.2
        elif temp_mean > 75:
            score += 0.1
        
        # Thermal throttling risk
        throttle_count = features.get('thermal_throttle_count', 0)
        if throttle_count > 20:
            score += 0.3
        elif throttle_count > 10:
            score += 0.15
        
        # ECC errors
        ecc_dbe = features.get('ecc_dbe_event_count', 0)
        if ecc_dbe > 0:
            score += 0.5  # Critical
        
        ecc_sbe = features.get('ecc_sbe_event_count', 0)
        if ecc_sbe > 100:
            score += 0.2
        
        # Age factor
        age_days = features.get('gpu_age_days', 0)
        if age_days > 1095:  # > 3 years
            score += 0.2
        elif age_days > 730:  # > 2 years
            score += 0.1
        
        return min(score, 0.95)
    
    def predict_failure_type(self, features: dict) -> str:
        """Predict most likely failure type."""
        scores = {
            'memory': 0.0,
            'thermal': 0.0,
            'power': 0.0,
            'other': 0.0
        }
        
        # Memory failure indicators
        ecc_dbe = features.get('ecc_dbe_event_count', 0)
        ecc_sbe = features.get('ecc_sbe_event_count', 0)
        if ecc_dbe > 0:
            scores['memory'] += 0.5
        if ecc_sbe > 50:
            scores['memory'] += 0.3
        
        # Thermal failure indicators
        temp_mean = features.get('gpu_temp_mean', 70)
        throttle_count = features.get('thermal_throttle_count', 0)
        if temp_mean > 85:
            scores['thermal'] += 0.4
        if throttle_count > 20:
            scores['thermal'] += 0.4
        
        # Power failure indicators
        power_brake = features.get('power_brake_count', 0)
        if power_brake > 10:
            scores['power'] += 0.5
        
        # Default to other if no clear signal
        if max(scores.values()) < 0.1:
            scores['other'] = 1.0
        
        return max(scores, key=scores.get)
    
    def save_predictions(self, predictions: list):
        """Save predictions to database."""
        if not predictions:
            return
        
        cursor = self.db_conn.cursor()
        
        for pred in predictions:
            cursor.execute("""
                INSERT INTO gpu_failure_predictions (
                    time, gpu_uuid, failure_prob_7d, failure_prob_30d, failure_prob_90d,
                    predicted_failure_type, estimated_ttf_days,
                    model_name, model_version, confidence
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (time, gpu_uuid) DO UPDATE SET
                    failure_prob_7d = EXCLUDED.failure_prob_7d,
                    failure_prob_30d = EXCLUDED.failure_prob_30d,
                    failure_prob_90d = EXCLUDED.failure_prob_90d,
                    predicted_failure_type = EXCLUDED.predicted_failure_type,
                    estimated_ttf_days = EXCLUDED.estimated_ttf_days,
                    confidence = EXCLUDED.confidence,
                    predicted_at = NOW()
            """, (
                datetime.now(),
                pred['gpu_uuid'],
                pred['failure_prob_7d'],
                pred['failure_prob_30d'],
                pred['failure_prob_90d'],
                pred['predicted_failure_type'],
                pred['estimated_ttf_days'],
                pred['model_name'],
                pred['model_version'],
                pred['confidence']
            ))
        
        self.db_conn.commit()
        logger.info(f"Saved {len(predictions)} failure predictions")
    
    def run(self):
        """Main prediction loop."""
        logger.info("Starting Failure Predictor Service")
        logger.info(f"Prediction interval: {PREDICTION_INTERVAL}s")
        logger.info(f"Model: {self.model is not None and 'XGBoost' or 'Heuristic'}")
        
        while True:
            try:
                logger.info("Starting failure prediction cycle")
                
                # Get list of active GPUs with features
                cursor = self.db_conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT gpu_uuid
                    FROM gpu_features
                    WHERE time >= NOW() - INTERVAL '24 hours'
                """)
                gpus = cursor.fetchall()
                
                logger.info(f"Predicting failures for {len(gpus)} GPUs")
                
                predictions = []
                for gpu in gpus:
                    gpu_uuid = gpu['gpu_uuid']
                    
                    pred = self.predict_failure(gpu_uuid)
                    if pred:
                        predictions.append(pred)
                        logger.info(f"GPU {gpu_uuid}: {pred['failure_prob_30d']:.1%} failure risk (30d), type: {pred['predicted_failure_type']}")
                
                # Save to database
                if predictions:
                    self.save_predictions(predictions)
                
                logger.info(f"Prediction cycle complete: {len(predictions)} predictions")
                
            except Exception as e:
                logger.error(f"Error in prediction cycle: {e}", exc_info=True)
            
            logger.info(f"Sleeping for {PREDICTION_INTERVAL}s")
            time.sleep(PREDICTION_INTERVAL)


if __name__ == '__main__':
    predictor = FailurePredictor()
    predictor.run()
