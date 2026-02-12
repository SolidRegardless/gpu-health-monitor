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
GPU Health Scorer
Computes multi-dimensional health scores (0-100) for each GPU based on recent metrics.
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict
import json
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values

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
SCORING_INTERVAL = int(os.getenv('SCORING_INTERVAL', '900'))  # 15 minutes
LOOKBACK_DAYS = int(os.getenv('LOOKBACK_DAYS', '7'))


@dataclass
class HealthScore:
    overall_score: float
    memory_health: float
    thermal_health: float
    performance_health: float
    power_health: float
    reliability_health: float
    health_grade: str
    degradation_factors: List[str]


class GPUHealthScorer:
    """
    Compute health scores using the algorithm from ml-pipeline-architecture.md
    """
    
    # Dimension weights
    WEIGHTS = {
        'memory': 0.30,
        'thermal': 0.25,
        'performance': 0.20,
        'power': 0.15,
        'reliability': 0.10
    }
    
    def __init__(self):
        self.db_conn = None
        self.connect_database()
    
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
    
    def get_active_gpus(self):
        """Get list of active GPUs from recent metrics."""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT DISTINCT gpu_uuid
                FROM gpu_metrics
                WHERE time > NOW() - INTERVAL '1 hour'
            """)
            return [row['gpu_uuid'] for row in cursor.fetchall()]
        except psycopg2.Error as e:
            logger.error(f"Failed to get active GPUs: {e}")
            return []
    
    def get_gpu_metrics(self, gpu_uuid: str, lookback_days: int = 7):
        """Get recent metrics for a GPU."""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT 
                    time,
                    gpu_temp,
                    memory_temp,
                    power_usage,
                    throttle_reasons,
                    fb_used_bytes,
                    fb_free_bytes,
                    ecc_sbe_volatile,
                    ecc_dbe_volatile,
                    ecc_sbe_aggregate,
                    ecc_dbe_aggregate,
                    retired_pages_dbe,
                    sm_active,
                    sm_occupancy,
                    tensor_active,
                    dram_active
                FROM gpu_metrics
                WHERE gpu_uuid = %s
                  AND time > NOW() - INTERVAL %s
                ORDER BY time ASC
            """, (gpu_uuid, f'{lookback_days} days'))
            
            return cursor.fetchall()
        except psycopg2.Error as e:
            logger.error(f"Failed to get GPU metrics: {e}")
            return []
    
    def score_memory_health(self, metrics) -> float:
        """
        Memory health (0-100):
        - ECC errors (critical)
        - Retired pages (critical)
        - Memory bandwidth degradation
        """
        if not metrics:
            return 0.0
        
        score = 100.0
        latest = metrics[-1]
        
        # Double-bit errors (uncorrectable) - critical
        dbe_count = latest['ecc_dbe_volatile'] or 0
        if dbe_count > 0:
            score -= min(50, dbe_count * 10)
        
        # Single-bit errors (correctable) - warning
        sbe_count = latest['ecc_sbe_volatile'] or 0
        if sbe_count > 100:
            score -= min(20, (sbe_count - 100) / 100 * 20)
        
        # Retired pages (permanent damage)
        retired_dbe = latest['retired_pages_dbe'] or 0
        if retired_dbe > 0:
            score -= min(30, retired_dbe * 5)
        
        # Memory bandwidth trend
        if len(metrics) > 1:
            recent_bw = sum(m['dram_active'] or 0 for m in metrics[-24:]) / min(24, len(metrics))
            baseline_bw = sum(m['dram_active'] or 0 for m in metrics[:24]) / min(24, len(metrics))
            
            if baseline_bw > 0:
                degradation = (baseline_bw - recent_bw) / baseline_bw
                if degradation > 0.1:
                    score -= degradation * 100
        
        return max(0, min(100, score))
    
    def score_thermal_health(self, metrics) -> float:
        """
        Thermal health (0-100):
        - Average temperature
        - Temperature spikes
        - Throttling events
        - Thermal stability
        """
        if not metrics:
            return 0.0
        
        score = 100.0
        
        # Average GPU temperature
        temps = [m['gpu_temp'] for m in metrics if m['gpu_temp'] is not None]
        if not temps:
            return 0.0
        
        avg_temp = sum(temps) / len(temps)
        
        # Temperature scoring
        if avg_temp > 85:
            score -= (avg_temp - 85) * 2
        elif avg_temp > 75:
            score -= (avg_temp - 75) * 1
        elif avg_temp < 30:
            score -= (30 - avg_temp) * 0.5
        
        # Max temperature (spikes)
        max_temp = max(temps)
        if max_temp > 95:
            score -= (max_temp - 95) * 3
        
        # Temperature variance (stability)
        if len(temps) > 1:
            temp_variance = sum((t - avg_temp) ** 2 for t in temps) / len(temps)
            temp_std = temp_variance ** 0.5
            if temp_std > 10:
                score -= (temp_std - 10) * 0.5
        
        # Throttling events
        throttle_count = sum(1 for m in metrics if (m['throttle_reasons'] or 0) > 0)
        throttle_pct = throttle_count / len(metrics) * 100
        
        if throttle_pct > 5:
            score -= throttle_pct
        
        # Hardware thermal throttling (critical)
        hw_thermal_throttle = sum(1 for m in metrics if ((m['throttle_reasons'] or 0) & (1 << 6)) > 0)
        if hw_thermal_throttle > 0:
            score -= 20
        
        return max(0, min(100, score))
    
    def score_performance_health(self, metrics) -> float:
        """
        Performance health (0-100):
        - Compute throughput
        - SM occupancy
        """
        if not metrics:
            return 0.0
        
        score = 100.0
        
        # SM active percentage
        sm_actives = [m['sm_active'] for m in metrics if m['sm_active'] is not None]
        if sm_actives:
            avg_sm_active = sum(sm_actives) / len(sm_actives)
        else:
            return 100.0
        
        # SM occupancy
        occupancies = [m['sm_occupancy'] for m in metrics if m['sm_occupancy'] is not None]
        if occupancies:
            avg_occupancy = sum(occupancies) / len(occupancies)
            
            # If GPU is being used but occupancy is low, penalize
            if avg_sm_active > 10 and avg_occupancy < 30:
                score -= (30 - avg_occupancy) * 0.5
        
        return max(0, min(100, score))
    
    def score_power_health(self, metrics) -> float:
        """
        Power health (0-100):
        - Power draw variance
        - Power throttling
        """
        if not metrics:
            return 0.0
        
        score = 100.0
        
        # Power variance (stability)
        powers = [m['power_usage'] for m in metrics if m['power_usage'] is not None]
        if not powers:
            return 100.0
        
        power_mean = sum(powers) / len(powers)
        
        if len(powers) > 1 and power_mean > 0:
            power_variance = sum((p - power_mean) ** 2 for p in powers) / len(powers)
            power_std = power_variance ** 0.5
            cv = power_std / power_mean
            
            if cv > 0.2:
                score -= (cv - 0.2) * 100
        
        # Power throttling
        power_throttle = sum(1 for m in metrics if ((m['throttle_reasons'] or 0) & (1 << 7)) > 0)
        if power_throttle > 0:
            score -= 15
        
        sw_power_cap = sum(1 for m in metrics if ((m['throttle_reasons'] or 0) & (1 << 2)) > 0)
        if sw_power_cap > len(metrics) * 0.5:
            score -= 10
        
        return max(0, min(100, score))
    
    def score_reliability_health(self, metrics) -> float:
        """
        Reliability health (0-100):
        - Sample completeness
        """
        if not metrics:
            return 0.0
        
        score = 100.0
        
        # Expected samples
        expected_samples = LOOKBACK_DAYS * 24 * 60 * 6  # 6 samples per minute
        actual_samples = len(metrics)
        
        completeness = actual_samples / expected_samples
        if completeness < 0.95:
            score -= (0.95 - completeness) * 100
        
        # Check for large time gaps
        if len(metrics) > 1:
            large_gaps = 0
            for i in range(1, len(metrics)):
                time_diff = (metrics[i]['time'] - metrics[i-1]['time']).total_seconds()
                if time_diff > 300:  # >5 minutes
                    large_gaps += 1
            
            if large_gaps > 0:
                score -= large_gaps * 5
        
        return max(0, min(100, score))
    
    def assign_grade(self, score: float) -> str:
        """Map numerical score to health grade."""
        if score >= 90:
            return "excellent"
        elif score >= 80:
            return "good"
        elif score >= 70:
            return "fair"
        elif score >= 60:
            return "degraded"
        elif score >= 50:
            return "poor"
        else:
            return "critical"
    
    def identify_degradation_factors(self, metrics, memory, thermal, performance, power, reliability) -> List[str]:
        """Identify specific factors causing degradation."""
        if not metrics:
            return []
        
        factors = []
        latest = metrics[-1]
        
        if (latest['ecc_dbe_volatile'] or 0) > 0:
            factors.append("uncorrectable_ecc_errors")
        
        if (latest['ecc_sbe_volatile'] or 0) > 100:
            factors.append("high_correctable_ecc_errors")
        
        temps = [m['gpu_temp'] for m in metrics if m['gpu_temp'] is not None]
        if temps and sum(temps) / len(temps) > 80:
            factors.append("elevated_temperature")
        
        hw_thermal = sum(1 for m in metrics if ((m['throttle_reasons'] or 0) & (1 << 6)) > 0)
        if hw_thermal > 0:
            factors.append("thermal_throttling")
        
        if (latest['retired_pages_dbe'] or 0) > 0:
            factors.append("retired_memory_pages")
        
        # Add dimension scores below thresholds
        if memory < 70:
            factors.append("memory_degradation")
        if thermal < 70:
            factors.append("thermal_issues")
        if performance < 70:
            factors.append("performance_degradation")
        
        return factors
    
    def score_gpu(self, gpu_uuid: str) -> HealthScore:
        """Compute health score for a single GPU."""
        logger.info(f"Scoring GPU: {gpu_uuid}")
        
        # Get metrics
        metrics = self.get_gpu_metrics(gpu_uuid, LOOKBACK_DAYS)
        
        if not metrics:
            logger.warning(f"No metrics found for GPU {gpu_uuid}")
            return HealthScore(
                overall_score=0.0,
                memory_health=0.0,
                thermal_health=0.0,
                performance_health=0.0,
                power_health=0.0,
                reliability_health=0.0,
                health_grade="unknown",
                degradation_factors=["no_data"]
            )
        
        # Compute dimension scores
        memory = self.score_memory_health(metrics)
        thermal = self.score_thermal_health(metrics)
        performance = self.score_performance_health(metrics)
        power = self.score_power_health(metrics)
        reliability = self.score_reliability_health(metrics)
        
        # Weighted overall score
        overall = (
            memory * self.WEIGHTS['memory'] +
            thermal * self.WEIGHTS['thermal'] +
            performance * self.WEIGHTS['performance'] +
            power * self.WEIGHTS['power'] +
            reliability * self.WEIGHTS['reliability']
        )
        
        # Grade
        grade = self.assign_grade(overall)
        
        # Degradation factors
        factors = self.identify_degradation_factors(
            metrics, memory, thermal, performance, power, reliability
        )
        
        logger.info(f"GPU {gpu_uuid} score: {overall:.1f} ({grade})")
        
        return HealthScore(
            overall_score=round(overall, 1),
            memory_health=round(memory, 1),
            thermal_health=round(thermal, 1),
            performance_health=round(performance, 1),
            power_health=round(power, 1),
            reliability_health=round(reliability, 1),
            health_grade=grade,
            degradation_factors=factors
        )
    
    def save_health_scores(self, scores: Dict[str, HealthScore]):
        """Save health scores to database."""
        if not scores:
            return
        
        try:
            cursor = self.db_conn.cursor()
            
            # Prepare data for batch insert
            now = datetime.now()
            rows = []
            
            for gpu_uuid, score in scores.items():
                rows.append((
                    now,
                    gpu_uuid,
                    score.overall_score,
                    score.health_grade,
                    score.memory_health,
                    score.thermal_health,
                    score.performance_health,
                    score.power_health,
                    score.reliability_health,
                    None,  # score_delta_7d (TODO: calculate from previous scores)
                    None,  # score_delta_30d
                    None,  # degradation_rate
                    json.dumps(score.degradation_factors),
                    '1.0'  # scoring_version
                ))
            
            execute_values(
                cursor,
                """
                INSERT INTO gpu_health_scores (
                    time, gpu_uuid, overall_score, health_grade,
                    memory_health, thermal_health, performance_health, power_health, reliability_health,
                    score_delta_7d, score_delta_30d, degradation_rate,
                    degradation_factors, scoring_version
                ) VALUES %s
                """,
                rows
            )
            
            self.db_conn.commit()
            logger.info(f"Saved health scores for {len(scores)} GPUs")
            
        except psycopg2.Error as e:
            logger.error(f"Failed to save health scores: {e}")
            self.db_conn.rollback()
    
    def run_scoring_cycle(self):
        """Run one health scoring cycle for all active GPUs."""
        logger.info("Starting health scoring cycle")
        
        # Get active GPUs
        gpus = self.get_active_gpus()
        logger.info(f"Found {len(gpus)} active GPUs")
        
        # Score each GPU
        scores = {}
        for gpu_uuid in gpus:
            try:
                score = self.score_gpu(gpu_uuid)
                scores[gpu_uuid] = score
            except Exception as e:
                logger.error(f"Error scoring GPU {gpu_uuid}: {e}", exc_info=True)
        
        # Save scores
        if scores:
            self.save_health_scores(scores)
        
        logger.info(f"Completed health scoring cycle: {len(scores)}/{len(gpus)} GPUs scored")
    
    def run(self):
        """Main scoring loop."""
        logger.info("Starting GPU Health Scorer")
        logger.info(f"Scoring interval: {SCORING_INTERVAL}s")
        logger.info(f"Lookback window: {LOOKBACK_DAYS} days")
        
        while True:
            try:
                self.run_scoring_cycle()
                
                logger.info(f"Sleeping for {SCORING_INTERVAL}s until next cycle")
                time.sleep(SCORING_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("Shutting down health scorer...")
                break
            except Exception as e:
                logger.error(f"Error in scoring loop: {e}", exc_info=True)
                logger.info(f"Retrying in {SCORING_INTERVAL}s...")
                time.sleep(SCORING_INTERVAL)
        
        # Cleanup
        if self.db_conn:
            self.db_conn.close()
        logger.info("Health scorer stopped")


if __name__ == '__main__':
    # Wait for database to be ready
    logger.info("Waiting for database to be ready...")
    time.sleep(20)
    
    scorer = GPUHealthScorer()
    scorer.run()
