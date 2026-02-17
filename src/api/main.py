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
GPU Health Monitor API
FastAPI service for querying GPU metrics and health scores.
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import anthropic

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

# Serve the HTML dashboard as static files if the /dashboard directory exists
import pathlib
_dashboard_dir = pathlib.Path("/app/dashboard")
if _dashboard_dir.exists():
    app.mount("/dashboard", StaticFiles(directory=str(_dashboard_dir), html=True), name="dashboard")

# Allow the standalone HTML dashboard (any localhost port) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
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


@app.get("/api/v1/market-intelligence")
def get_market_intelligence():
    """
    Generate AI-powered secondary market intelligence commentary.
    Pulls current GPU prices, fleet health and NPV decisions from the DB,
    then asks Claude to write fresh market analysis as HTML paragraphs.
    Streams the response so the UI can render text progressively.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    # No early-exit on missing key — we fall back to template commentary below

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # ── Current secondary market prices ───────────────────────────────────
        cursor.execute("""
            SELECT model, condition, price_low_usd, price_high_usd, price_mid_usd,
                   original_cost_usd, source,
                   TO_CHAR(fetched_at, 'DD Mon YYYY HH24:MI UTC') as fetched_at
            FROM v_latest_market_prices
            WHERE condition = 'used_good'
            ORDER BY model
        """)
        prices = [dict(r) for r in cursor.fetchall()]

        # ── Fleet decision summary ────────────────────────────────────────────
        cursor.execute("""
            SELECT decision, COUNT(*) as count,
                   ROUND(AVG(health_score)::numeric, 1) as avg_health,
                   ROUND(AVG(npv_sell)::numeric, 0)  as avg_npv_sell,
                   ROUND(AVG(npv_keep)::numeric, 0)  as avg_npv_keep
            FROM v_latest_economic_decisions
            GROUP BY decision
            ORDER BY count DESC
        """)
        decisions = [dict(r) for r in cursor.fetchall()]

        # ── Per-model breakdown ───────────────────────────────────────────────
        cursor.execute("""
            SELECT a.model,
                   COUNT(*) as total,
                   SUM(CASE WHEN d.decision = 'sell'      THEN 1 ELSE 0 END) as sell_count,
                   SUM(CASE WHEN d.decision = 'keep'      THEN 1 ELSE 0 END) as keep_count,
                   SUM(CASE WHEN d.decision = 'repurpose' THEN 1 ELSE 0 END) as repurpose_count,
                   ROUND(AVG(h.overall_score)::numeric, 1)  as avg_health
            FROM gpu_assets a
            JOIN v_latest_economic_decisions d ON a.gpu_uuid = d.gpu_uuid
            JOIN gpu_health_scores h ON a.gpu_uuid = h.gpu_uuid
            WHERE h.time = (SELECT MAX(h2.time) FROM gpu_health_scores h2 WHERE h2.gpu_uuid = h.gpu_uuid)
            GROUP BY a.model
            ORDER BY a.model
        """)
        model_breakdown = [dict(r) for r in cursor.fetchall()]

    except Exception as e:
        logger.error(f"DB error in market-intelligence: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # ── Build prompt ──────────────────────────────────────────────────────────
    price_lines = "\n".join(
        f"  - {p['model']}: secondary market ${p['price_low_usd']:,.0f}–${p['price_high_usd']:,.0f} "
        f"(mid ${p['price_mid_usd']:,.0f}), original new price ${p['original_cost_usd']:,.0f}, "
        f"data as of {p['fetched_at']} (source: {p['source']})"
        for p in prices
    ) or "  No live pricing data available yet."

    decision_lines = "\n".join(
        f"  - {d['decision'].upper()}: {d['count']} GPU(s), "
        f"avg health {d['avg_health']}/100, avg NPV sell ${d['avg_npv_sell']:,.0f}, avg NPV keep ${d['avg_npv_keep']:,.0f}"
        for d in decisions
    ) or "  No decision data yet."

    model_lines = "\n".join(
        f"  - {m['model']}: {m['total']} units, avg health {m['avg_health']}/100 "
        f"[KEEP: {m['keep_count']} | SELL: {m['sell_count']} | REPURPOSE: {m['repurpose_count']}]"
        for m in model_breakdown
    ) or "  No model breakdown available."

    prompt = f"""You are a GPU fleet economics analyst writing a brief market intelligence summary for an operational dashboard.

Current secondary market GPU pricing (live data):
{price_lines}

Current fleet decision summary:
{decision_lines}

Fleet breakdown by model:
{model_lines}

Write exactly 3 short paragraphs of market intelligence commentary in plain HTML (use only <p> and <strong> tags).
Each paragraph should cover one of these angles:
1. What the current secondary market prices tell us about supply/demand dynamics — reference the actual prices above and any relevant macro trends (Blackwell ramp, hyperscaler offloading, etc.)
2. What the fleet health and NPV data tells us — interpret the KEEP/SELL/REPURPOSE split, reference the average health scores, and explain what this means for the operator
3. A forward-looking view: given current trends, what should the operator watch for over the next 3–6 months to maximise residual value recovery

Be concise, factual, and commercially sharp. No bullet points. No headings. No markdown. Just 3 <p> tags.
Reference the actual numbers from the data above where relevant."""

    # ── Template fallback (no Claude needed) ─────────────────────────────────
    def _template_commentary() -> str:
        """Generate data-driven commentary without Claude — fallback only."""
        total_gpus = sum(d.get("count", 0) for d in decisions)
        sell_count = next((d["count"] for d in decisions if d["decision"] == "sell"), 0)
        keep_count = next((d["count"] for d in decisions if d["decision"] == "keep"), 0)
        repurpose_count = next((d["count"] for d in decisions if d["decision"] == "repurpose"), 0)
        sell_pct = round(sell_count / total_gpus * 100) if total_gpus else 0

        a100_price = next((p["price_mid_usd"] for p in prices if "A100" in p["model"]), 8500)
        h100_price = next((p["price_mid_usd"] for p in prices if "H100" in p["model"]), 24000)
        a100_orig  = next((p["original_cost_usd"] for p in prices if "A100" in p["model"]), 15000)
        h100_orig  = next((p["original_cost_usd"] for p in prices if "H100" in p["model"]), 32000)
        a100_pct   = round(a100_price / a100_orig * 100)
        h100_pct   = round(h100_price / h100_orig * 100)

        a100_model = next((m for m in model_breakdown if "A100" in m["model"]), {})
        h100_model = next((m for m in model_breakdown if "H100" in m["model"]), {})
        avg_health_a = a100_model.get("avg_health", 70)
        avg_health_h = h100_model.get("avg_health", 75)

        p1 = (
            f"<p>Secondary market GPU pricing continues to reflect structural demand shifts driven by the "
            f"Hopper-to-Blackwell architecture transition. <strong>A100 SXM4-80GB units are trading at "
            f"${a100_price:,.0f}</strong> — approximately {a100_pct}% of original list — as hyperscalers "
            f"rotate ageing Ampere capacity toward next-generation deployments. "
            f"<strong>H100 SXM5-80GB units command ${h100_price:,.0f}</strong> ({h100_pct}% of new cost), "
            f"supported by sustained inference workload demand and constrained supply from TSMC CoWoS packaging. "
            f"The A100/H100 price spread of ${h100_price - a100_price:,.0f} signals the market is pricing "
            f"in a meaningful compute-density premium for FP8 tensor cores.</p>"
        )

        if sell_pct >= 60:
            fleet_sentiment = "weighted toward capital recovery"
            fleet_detail = (
                f"With {sell_pct}% of the fleet flagged for liquidation, the economic engine is prioritising "
                f"residual value capture over continued depreciation."
            )
        elif sell_pct >= 30:
            fleet_sentiment = "balanced between retention and realisation"
            fleet_detail = (
                f"The mixed {keep_count} KEEP / {sell_count} SELL / {repurpose_count} REPURPOSE split indicates "
                f"a fleet in transition — healthy units are retained for workload continuity while degraded "
                f"assets are routed to secondary markets before further depreciation."
            )
        else:
            fleet_sentiment = "strongly weighted toward retention"
            fleet_detail = (
                f"With only {sell_count} unit(s) flagged for liquidation, current economics favour keeping "
                f"the fleet operational; the NPV of continued utilisation exceeds secondary market realisable value."
            )

        p2 = (
            f"<p>Fleet health analytics position current decision-making as <strong>{fleet_sentiment}</strong>. "
            f"A100 average health score stands at {avg_health_a}/100, H100 at {avg_health_h}/100. "
            f"{fleet_detail} "
            f"The economic engine caps failure probability at 60% to prevent ML cold-start bias from "
            f"over-penalising NPV Keep, ensuring decisions reflect structural degradation rather than "
            f"transient sensor noise.</p>"
        )

        months_at_rate = round(sell_count / max(total_gpus, 1) * 18)
        p3 = (
            f"<p>Looking ahead 3–6 months, operators should monitor Blackwell GB200 NVL72 ramp timelines — "
            f"accelerated availability will compress H100 secondary market prices by an estimated 15–25% "
            f"as enterprise buyers gain alternatives. A100 pricing is likely to stabilise near "
            f"${max(a100_price - 500, 5000):,.0f}–${a100_price:,.0f} as a floor driven by inference "
            f"inference economics at mid-market cloud providers. <strong>Key action: prioritise "
            f"SELL-flagged units within the next 60–90 days</strong> to capture current bid-side liquidity "
            f"before Blackwell supply normalisation depresses comparable Ampere valuations further. "
            f"Repurpose candidates should be evaluated for edge deployment or HPC rental markets where "
            f"FP64 workloads make A100 economics competitive with newer architectures.</p>"
        )
        return p1 + p2 + p3

    # ── Stream Claude's response (with template fallback) ────────────────────
    def stream_claude():
        if not api_key:
            yield _template_commentary()
            return
        try:
            client = anthropic.Anthropic(api_key=api_key)
            with client.messages.stream(
                model="claude-3-5-haiku-20241022",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except anthropic.AuthenticationError:
            logger.warning("Anthropic auth failed — using template commentary fallback")
            yield _template_commentary()
        except Exception as e:
            logger.warning(f"Claude API error ({e}) — using template commentary fallback")
            yield _template_commentary()

    return StreamingResponse(stream_claude(), media_type="text/html; charset=utf-8")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
