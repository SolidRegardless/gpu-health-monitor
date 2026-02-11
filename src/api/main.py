#!/usr/bin/env python3
"""
GPU Health Monitor API
FastAPI service for querying GPU metrics and health scores.
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DB_HOST = os.getenv('DB_HOST', 'timescaledb')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'gpu_health')
DB_USER = os.getenv('DB_USER', 'gpu_monitor')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'gpu_monitor_secret')

# FastAPI app
app = FastAPI(
    title="GPU Health Monitor API",
    description="API for querying GPU metrics and health scores",
    version="1.0.0"
)

# Database connection pool
db_conn = None


def get_db_connection():
    """Get database connection."""
    global db_conn
    
    if db_conn is None or db_conn.closed:
        db_conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
    
    return db_conn


# Response models
class GPUInfo(BaseModel):
    gpu_uuid: str
    hostname: Optional[str]
    model: Optional[str]
    last_seen: Optional[datetime]


class MetricSample(BaseModel):
    time: datetime
    gpu_temp: Optional[float]
    memory_temp: Optional[float]
    power_usage: Optional[float]
    sm_active: Optional[float]
    memory_utilization: Optional[float]


class HealthScoreResponse(BaseModel):
    time: datetime
    gpu_uuid: str
    overall_score: float
    health_grade: str
    memory_health: Optional[float]
    thermal_health: Optional[float]
    performance_health: Optional[float]
    power_health: Optional[float]
    reliability_health: Optional[float]
    degradation_factors: Optional[List[str]]


class FleetSummary(BaseModel):
    total_gpus: int
    avg_temp: Optional[float]
    max_temp: Optional[float]
    avg_power: Optional[float]
    throttling_count: int
    dbe_error_count: int


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "service": "GPU Health Monitor API",
        "version": "1.0.0",
        "endpoints": {
            "gpus": "/api/v1/gpus",
            "metrics": "/api/v1/gpus/{gpu_uuid}/metrics",
            "health": "/api/v1/gpus/{gpu_uuid}/health",
            "fleet": "/api/v1/fleet/summary"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


@app.get("/api/v1/gpus", response_model=List[GPUInfo])
def list_gpus():
    """List all GPUs with recent data."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT
                m.gpu_uuid,
                m.hostname,
                a.model,
                MAX(m.time) as last_seen
            FROM gpu_metrics m
            LEFT JOIN gpu_assets a ON m.gpu_uuid = a.gpu_uuid
            WHERE m.time > NOW() - INTERVAL '24 hours'
            GROUP BY m.gpu_uuid, m.hostname, a.model
            ORDER BY m.gpu_uuid
        """)
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
        
    except Exception as e:
        logger.error(f"Error listing GPUs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/gpus/{gpu_uuid}/metrics", response_model=List[MetricSample])
def get_gpu_metrics(
    gpu_uuid: str,
    hours: int = Query(default=1, ge=1, le=168, description="Hours of data to retrieve (max 7 days)")
):
    """Get recent metrics for a GPU."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                time,
                gpu_temp,
                memory_temp,
                power_usage,
                sm_active,
                memory_utilization
            FROM gpu_metrics
            WHERE gpu_uuid = %s
              AND time > NOW() - INTERVAL %s
            ORDER BY time DESC
            LIMIT 1000
        """, (gpu_uuid, f'{hours} hours'))
        
        rows = cursor.fetchall()
        
        if not rows:
            raise HTTPException(status_code=404, detail=f"No metrics found for GPU {gpu_uuid}")
        
        return [dict(row) for row in rows]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/gpus/{gpu_uuid}/health", response_model=List[HealthScoreResponse])
def get_gpu_health(
    gpu_uuid: str,
    limit: int = Query(default=10, ge=1, le=100, description="Number of scores to retrieve")
):
    """Get recent health scores for a GPU."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                time,
                gpu_uuid,
                overall_score,
                health_grade,
                memory_health,
                thermal_health,
                performance_health,
                power_health,
                reliability_health,
                degradation_factors
            FROM gpu_health_scores
            WHERE gpu_uuid = %s
            ORDER BY time DESC
            LIMIT %s
        """, (gpu_uuid, limit))
        
        rows = cursor.fetchall()
        
        if not rows:
            raise HTTPException(status_code=404, detail=f"No health scores found for GPU {gpu_uuid}")
        
        return [dict(row) for row in rows]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting health scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/fleet/summary", response_model=FleetSummary)
def get_fleet_summary():
    """Get current fleet-wide summary."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM v_fleet_health_summary
        """)
        
        row = cursor.fetchone()
        
        if not row:
            return FleetSummary(
                total_gpus=0,
                avg_temp=None,
                max_temp=None,
                avg_power=None,
                throttling_count=0,
                dbe_error_count=0
            )
        
        return dict(row)
        
    except Exception as e:
        logger.error(f"Error getting fleet summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/gpus/{gpu_uuid}/stats")
def get_gpu_stats(gpu_uuid: str, hours: int = Query(default=24, ge=1, le=168)):
    """Get statistical summary for a GPU over a time period."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT
                COUNT(*) as sample_count,
                AVG(gpu_temp) as avg_temp,
                MIN(gpu_temp) as min_temp,
                MAX(gpu_temp) as max_temp,
                AVG(power_usage) as avg_power,
                MAX(power_usage) as max_power,
                AVG(sm_active) as avg_utilization,
                SUM(CASE WHEN throttle_reasons > 0 THEN 1 ELSE 0 END) as throttle_events,
                SUM(CASE WHEN ecc_dbe_volatile > 0 THEN 1 ELSE 0 END) as dbe_error_events
            FROM gpu_metrics
            WHERE gpu_uuid = %s
              AND time > NOW() - INTERVAL %s
        """, (gpu_uuid, f'{hours} hours'))
        
        row = cursor.fetchone()
        
        if not row or row['sample_count'] == 0:
            raise HTTPException(status_code=404, detail=f"No data found for GPU {gpu_uuid}")
        
        return dict(row)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting GPU stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/alerts")
def get_alerts():
    """Get current alerts (GPUs with health issues)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            WITH latest_scores AS (
                SELECT DISTINCT ON (gpu_uuid)
                    gpu_uuid,
                    overall_score,
                    health_grade,
                    degradation_factors,
                    time
                FROM gpu_health_scores
                ORDER BY gpu_uuid, time DESC
            )
            SELECT 
                ls.gpu_uuid,
                a.model,
                a.hostname,
                ls.overall_score,
                ls.health_grade,
                ls.degradation_factors,
                ls.time as scored_at
            FROM latest_scores ls
            LEFT JOIN gpu_assets a ON ls.gpu_uuid = a.gpu_uuid
            WHERE ls.overall_score < 70
            ORDER BY ls.overall_score ASC
        """)
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
