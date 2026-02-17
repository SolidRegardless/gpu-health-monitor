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
Economic Decision Engine
NPV-based lifecycle recommendations for GPU fleet management.
"""

import os
import sys
import time
import logging
import json
from datetime import datetime, timedelta
from enum import Enum
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
ANALYSIS_INTERVAL = int(os.getenv('ANALYSIS_INTERVAL', '86400'))  # 24 hours


class LifecycleDecision(str, Enum):
    KEEP = "keep"
    SELL = "sell"
    REPURPOSE = "repurpose"
    DECOMMISSION = "decommission"


class EconomicDecisionEngine:
    """NPV-based lifecycle decision engine for GPU fleet."""

    # Model-specific secondary market residual values (USD).
    # Reflects current broker / secondary market pricing for used GPU hardware.
    # A100 SXM4-80GB trades at roughly 30-40% of H100 SXM5-80GB on secondary markets (Feb 2026).
    RESIDUAL_VALUE_BY_MODEL = {
        'NVIDIA A100-SXM4-80GB': {
            'excellent': 13500,  # 90-100 health — near-new A100, top-tier secondary
            'good':      10500,  # 80-89
            'fair':       8500,  # 70-79
            'degraded':   5700,  # 60-69
            'poor':       3000,  # 50-59
            'critical':    800,  # < 50
        },
        'NVIDIA H100-SXM5-80GB': {
            'excellent': 32000,  # 90-100 health
            'good':      28000,  # 80-89
            'fair':      22000,  # 70-79
            'degraded':  15000,  # 60-69
            'poor':       8000,  # 50-59
            'critical':   2000,  # < 50
        },
    }
    # Fallback for unknown models — conservative mid-range values
    RESIDUAL_VALUE_DEFAULT = {
        'excellent': 20000,
        'good':      16000,
        'fair':      12000,
        'degraded':   8000,
        'poor':       4000,
        'critical':   1000,
    }

    # Keep for backward-compat references elsewhere in the codebase
    RESIDUAL_VALUE = RESIDUAL_VALUE_BY_MODEL['NVIDIA H100-SXM5-80GB']

    # Maximum failure probability used in NPV penalty — cap at 60%.
    # A 60% 90-day failure probability is already a decisive sell signal;
    # capping prevents an un-warmed ML model from producing absurd penalties.
    FAILURE_PROB_CAP = 0.60
    
    # Operating costs (monthly)
    POWER_COST_PER_KWH = 0.12  # $0.12/kWh
    COOLING_PUE = 1.3          # Power Usage Effectiveness
    POWER_WATTS = 350          # Average power draw
    MAINTENANCE_COST = 50      # $50/month per GPU
    
    # Revenue assumptions
    REVENUE_PER_GPU_HOUR_FULL = 3.00      # $3/hour at 100% utilization (training)
    REVENUE_PER_GPU_HOUR_INFERENCE = 2.00  # $2/hour for inference workloads
    
    # Discount rate for NPV
    ANNUAL_DISCOUNT_RATE = 0.10  # 10% annual discount rate
    
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
    
    def get_gpu_context(self, gpu_uuid: str) -> dict:
        """Get all context needed for economic decision."""
        cursor = self.db_conn.cursor()
        
        # Get latest health score
        cursor.execute("""
            SELECT overall_score, health_grade, memory_health, thermal_health
            FROM gpu_health_scores
            WHERE gpu_uuid = %s
            ORDER BY time DESC
            LIMIT 1
        """, (gpu_uuid,))
        health = cursor.fetchone()
        
        # Get latest failure prediction
        cursor.execute("""
            SELECT failure_prob_30d, failure_prob_90d, predicted_failure_type, estimated_ttf_days
            FROM gpu_failure_predictions
            WHERE gpu_uuid = %s
            ORDER BY time DESC
            LIMIT 1
        """, (gpu_uuid,))
        prediction = cursor.fetchone()
        
        # Get asset metadata
        cursor.execute("""
            SELECT model, deployment_date, warranty_expiry, purchase_date
            FROM gpu_assets
            WHERE gpu_uuid = %s
        """, (gpu_uuid,))
        asset = cursor.fetchone()
        
        # Get recent utilization
        cursor.execute("""
            SELECT AVG(sm_active) as avg_utilization
            FROM gpu_metrics
            WHERE gpu_uuid = %s
              AND time >= NOW() - INTERVAL '30 days'
        """, (gpu_uuid,))
        util = cursor.fetchone()
        
        return {
            'health': dict(health) if health else {},
            'prediction': dict(prediction) if prediction else {},
            'asset': dict(asset) if asset else {},
            'utilization': util['avg_utilization'] if util and util['avg_utilization'] else 0.5
        }
    
    def _residual_values(self, model: str) -> dict:
        """Return the correct residual value table for the given GPU model."""
        return self.RESIDUAL_VALUE_BY_MODEL.get(model, self.RESIDUAL_VALUE_DEFAULT)

    def calculate_npv_keep(
        self,
        health_score: float,
        failure_prob_90d: float,
        utilization: float,
        months: int = 12,
        model: str = '',
    ) -> float:
        """
        Calculate NPV of keeping the GPU for specified months.

        NPV(Keep) = Revenue - Costs - Failure_Risk
        """
        monthly_discount = (1 + self.ANNUAL_DISCOUNT_RATE) ** (1/12) - 1
        residuals = self._residual_values(model)

        # Cap failure probability — an un-warmed predictor can output 0.99;
        # 60% is already a decisive sell signal and prevents absurd NPV penalties.
        failure_prob_capped = min(failure_prob_90d, self.FAILURE_PROB_CAP)

        npv = 0.0

        for month in range(months):
            # Monthly revenue (hours * rate * utilization fraction)
            hours_per_month = 730
            monthly_revenue = hours_per_month * self.REVENUE_PER_GPU_HOUR_FULL * (utilization / 100)

            # Monthly costs
            power_cost = (self.POWER_WATTS / 1000) * hours_per_month * self.POWER_COST_PER_KWH * self.COOLING_PUE
            total_cost = power_cost + self.MAINTENANCE_COST

            # Net cash flow before health/risk adjustments
            net_cash_flow = monthly_revenue - total_cost

            # Discount factor
            discount_factor = 1 / ((1 + monthly_discount) ** month)

            # Adjust for health degradation (linear decline assumption)
            health_factor = max(0.2, (health_score - month * 2) / 100)

            # Failure risk: expected loss from GPU failure, using model-specific value
            failure_risk = failure_prob_capped * residuals.get('fair', 12000)

            npv += (net_cash_flow * health_factor - failure_risk / months) * discount_factor

        return npv

    def calculate_npv_sell(self, health_grade: str, model: str = '') -> float:
        """
        Calculate NPV of selling GPU now on the secondary market.

        NPV(Sell) = Market_Value - Transaction_Costs
        Uses model-specific secondary market pricing.
        """
        residuals = self._residual_values(model)
        market_value = residuals.get(health_grade, residuals.get('fair', 10000))
        transaction_costs = market_value * 0.05  # 5% broker/transaction fee
        return market_value - transaction_costs

    def calculate_npv_repurpose(
        self,
        health_score: float,
        failure_prob_90d: float,
        months: int = 12,
        model: str = '',
    ) -> float:
        """
        Calculate NPV of repurposing for lower-tier workloads (inference).

        NPV(Repurpose) = Lower_Revenue - Costs - Failure_Risk
        """
        monthly_discount = (1 + self.ANNUAL_DISCOUNT_RATE) ** (1/12) - 1
        residuals = self._residual_values(model)
        failure_prob_capped = min(failure_prob_90d, self.FAILURE_PROB_CAP)

        npv = 0.0

        for month in range(months):
            hours_per_month = 730
            monthly_revenue = hours_per_month * self.REVENUE_PER_GPU_HOUR_INFERENCE * 0.7
            power_cost = (self.POWER_WATTS / 1000) * hours_per_month * self.POWER_COST_PER_KWH * self.COOLING_PUE
            total_cost = power_cost + self.MAINTENANCE_COST * 0.8
            net_cash_flow = monthly_revenue - total_cost
            discount_factor = 1 / ((1 + monthly_discount) ** month)
            health_factor = max(0.3, (health_score - month) / 100)
            failure_risk = failure_prob_capped * residuals.get('fair', 12000)
            npv += (net_cash_flow * health_factor - failure_risk / months) * discount_factor

        return npv
    
    def analyze_gpu(self, gpu_uuid: str) -> dict:
        """
        Perform comprehensive economic analysis for a GPU.
        
        Returns decision recommendation with NPV calculations.
        """
        logger.info(f"Analyzing GPU {gpu_uuid}")
        
        # Get context
        context = self.get_gpu_context(gpu_uuid)
        
        if not context['health']:
            logger.warning(f"No health data for GPU {gpu_uuid}")
            return None
        
        health_score = context['health'].get('overall_score', 70)
        health_grade = context['health'].get('health_grade', 'fair')
        failure_prob_30d = context['prediction'].get('failure_prob_30d', 0.1) if context['prediction'] else 0.1
        failure_prob_90d = context['prediction'].get('failure_prob_90d', 0.2) if context['prediction'] else 0.2
        utilization = context['utilization']
        model = context['asset'].get('model', '') if context['asset'] else ''

        logger.info(f"  Model: {model}, Health: {health_score:.1f} ({health_grade}), "
                    f"Util: {utilization:.1f}%, FailProb90d: {failure_prob_90d:.3f}")

        # Calculate NPVs for each option (all model-aware)
        npv_keep = self.calculate_npv_keep(health_score, failure_prob_90d, utilization, months=12, model=model)
        npv_sell = self.calculate_npv_sell(health_grade, model=model)
        npv_repurpose = self.calculate_npv_repurpose(health_score, failure_prob_90d, months=12, model=model)

        # Salvage value (decommission) — 10% of model-specific market value
        salvage_value = self._residual_values(model).get(health_grade, 5000) * 0.1
        
        # Choose best decision
        options = {
            LifecycleDecision.KEEP: npv_keep,
            LifecycleDecision.SELL: npv_sell,
            LifecycleDecision.REPURPOSE: npv_repurpose,
            LifecycleDecision.DECOMMISSION: salvage_value
        }
        
        best_decision = max(options, key=options.get)
        expected_value = options[best_decision]
        
        # Calculate confidence (based on difference between top 2 options)
        sorted_values = sorted(options.values(), reverse=True)
        if len(sorted_values) > 1 and sorted_values[0] > 0:
            gap = sorted_values[0] - sorted_values[1]
            confidence = min(0.95, 0.5 + (gap / sorted_values[0]) * 0.5)
        else:
            confidence = 0.5
        
        # Generate rationale
        rationale = self.generate_rationale(
            best_decision, health_score, failure_prob_30d, utilization, npv_keep, npv_sell
        )
        
        result = {
            'gpu_uuid': gpu_uuid,
            'decision': best_decision.value,
            'npv_keep': round(npv_keep, 2),
            'npv_sell': round(npv_sell, 2),
            'npv_repurpose': round(npv_repurpose, 2),
            'salvage_value': round(salvage_value, 2),
            'expected_value': round(expected_value, 2),
            'confidence': round(confidence, 2),
            'rationale': rationale,
            'health_score': health_score,
            'failure_prob_30d': failure_prob_30d,
            'utilization': utilization
        }
        
        logger.info(f"GPU {gpu_uuid}: Decision={best_decision.value}, EV=${expected_value:.2f}, Confidence={confidence:.0%}")
        
        return result
    
    def generate_rationale(
        self,
        decision: LifecycleDecision,
        health_score: float,
        failure_prob: float,
        utilization: float,
        npv_keep: float,
        npv_sell: float
    ) -> str:
        """Generate human-readable rationale for decision."""
        
        if decision == LifecycleDecision.KEEP:
            return (f"Recommended to KEEP: Health score {health_score:.1f}/100 is good, "
                    f"failure risk {failure_prob:.1%} is acceptable, "
                    f"NPV of continued operation (${npv_keep:.0f}) exceeds resale value (${npv_sell:.0f}).")
        
        elif decision == LifecycleDecision.SELL:
            return (f"Recommended to SELL: Current market value (${npv_sell:.0f}) exceeds "
                    f"future operating value (${npv_keep:.0f}). "
                    f"Health score {health_score:.1f}/100, failure risk {failure_prob:.1%}.")
        
        elif decision == LifecycleDecision.REPURPOSE:
            return (f"Recommended to REPURPOSE: Health score {health_score:.1f}/100 too low for training, "
                    f"but suitable for inference workloads. Failure risk {failure_prob:.1%}.")
        
        else:  # DECOMMISSION
            return (f"Recommended to DECOMMISSION: Health score {health_score:.1f}/100 critical, "
                    f"failure risk {failure_prob:.1%} too high. Salvage for parts.")
    
    def save_decision(self, analysis: dict):
        """Save economic analysis to database."""
        if not analysis:
            return
        
        cursor = self.db_conn.cursor()
        
        cursor.execute("""
            INSERT INTO gpu_economic_decisions (
                time, gpu_uuid, decision, npv_keep, npv_sell, npv_repurpose,
                salvage_value, expected_value, confidence, rationale,
                health_score, failure_prob_30d, utilization
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (time, gpu_uuid) DO UPDATE SET
                decision = EXCLUDED.decision,
                expected_value = EXCLUDED.expected_value,
                confidence = EXCLUDED.confidence,
                analyzed_at = NOW()
        """, (
            datetime.now(),
            analysis['gpu_uuid'],
            analysis['decision'],
            analysis['npv_keep'],
            analysis['npv_sell'],
            analysis['npv_repurpose'],
            analysis['salvage_value'],
            analysis['expected_value'],
            analysis['confidence'],
            analysis['rationale'],
            analysis['health_score'],
            analysis['failure_prob_30d'],
            analysis['utilization']
        ))
        
        self.db_conn.commit()
    
    def run(self):
        """Main analysis loop."""
        logger.info("Starting Economic Decision Engine")
        logger.info(f"Analysis interval: {ANALYSIS_INTERVAL}s")
        
        while True:
            try:
                logger.info("Starting economic analysis cycle")
                
                # Get all GPUs with health scores
                cursor = self.db_conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT gpu_uuid
                    FROM gpu_health_scores
                    WHERE time >= NOW() - INTERVAL '24 hours'
                """)
                gpus = cursor.fetchall()
                
                logger.info(f"Analyzing {len(gpus)} GPUs")
                
                decisions = {}
                for gpu in gpus:
                    gpu_uuid = gpu['gpu_uuid']
                    
                    analysis = self.analyze_gpu(gpu_uuid)
                    
                    if analysis:
                        self.save_decision(analysis)
                        decisions[analysis['decision']] = decisions.get(analysis['decision'], 0) + 1
                
                logger.info(f"Analysis complete. Decisions: {decisions}")
                
            except Exception as e:
                logger.error(f"Error in analysis cycle: {e}", exc_info=True)
            
            logger.info(f"Sleeping for {ANALYSIS_INTERVAL}s")
            time.sleep(ANALYSIS_INTERVAL)


if __name__ == '__main__':
    engine = EconomicDecisionEngine()
    engine.run()
