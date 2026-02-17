#!/usr/bin/env python3
"""
market_price_fetcher.py
-----------------------
Fetches secondary-market GPU prices from web sources and persists them to
the gpu_market_prices TimescaleDB table.

Sources:
  1. JarvisLabs A100 FAQ   – https://jarvislabs.ai/ai-faqs/nvidia-a100-gpu-price
  2. JarvisLabs H100 blog  – https://docs.jarvislabs.ai/blog/h100-price
  3. Fallback              – hardcoded realistic 2026 market values

Schedule: runs once on startup, then every FETCH_INTERVAL_HOURS hours.
"""

import logging
import os
import re
import time
from datetime import datetime
from typing import Optional, Tuple

import anthropic
import psycopg2
import requests
from bs4 import BeautifulSoup

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("market-price-fetcher")

# ─── Configuration ────────────────────────────────────────────────────────────

DB_HOST             = os.environ.get("DB_HOST", "localhost")
DB_PORT             = int(os.environ.get("DB_PORT", "5432"))
DB_NAME             = os.environ.get("DB_NAME", "gpu_health")
DB_USER             = os.environ.get("DB_USER", "gpu_monitor")
DB_PASSWORD         = os.environ.get("DB_PASSWORD", "gpu_monitor_secret")
FETCH_INTERVAL_HRS  = float(os.environ.get("FETCH_INTERVAL_HOURS", "6"))

HTTP_TIMEOUT        = 10   # seconds
HTTP_HEADERS        = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ─── Fallback prices (2026 market estimates) ──────────────────────────────────

FALLBACK_PRICES = {
    "NVIDIA A100-SXM4-80GB": {
        "condition":          "used_good",
        "price_low_usd":      7000.00,
        "price_high_usd":     10000.00,
        "price_mid_usd":      8500.00,
        "original_cost_usd":  15000.00,
    },
    "NVIDIA H100-SXM5-80GB": {
        "condition":          "used_good",
        "price_low_usd":      20000.00,
        "price_high_usd":     28000.00,
        "price_mid_usd":      24000.00,
        "original_cost_usd":  32000.00,
    },
}

# ─── Price parsing helpers ────────────────────────────────────────────────────

def _clean_number(s: str) -> float:
    """Strip '$', commas and whitespace, return float."""
    return float(s.replace("$", "").replace(",", "").strip())


def parse_price_range(text: str) -> Optional[Tuple[float, float, float]]:
    """
    Extract (low, high, mid) from text containing patterns like:
      $7,000–$10,000   $7,000-$10,000   $7000-$10000   $24,000
    Returns None when no price found.
    """
    # Range pattern: $X[-–]$Y
    range_pat = re.compile(
        r"\$[\d,]+\s*[-\u2013\u2014]\s*\$[\d,]+",
        re.IGNORECASE,
    )
    single_pat = re.compile(r"\$[\d,]+", re.IGNORECASE)

    m = range_pat.search(text)
    if m:
        parts = re.findall(r"\$[\d,]+", m.group())
        if len(parts) >= 2:
            lo = _clean_number(parts[0])
            hi = _clean_number(parts[1])
            return lo, hi, round((lo + hi) / 2, 2)

    m = single_pat.search(text)
    if m:
        val = _clean_number(m.group())
        return val, val, val

    return None


# ─── Web scrapers ─────────────────────────────────────────────────────────────

def fetch_a100_price() -> Optional[Tuple[float, float, float]]:
    """Scrape JarvisLabs A100 price FAQ for used-market range."""
    url = "https://jarvislabs.ai/ai-faqs/nvidia-a100-gpu-price"
    log.info("Fetching A100 price from %s", url)
    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        text = soup.get_text(" ", strip=True)

        # Look for text around "Used" or "secondary" sections
        # The page contains "Used (Good Condition) 80GB $7,000-$10,000"
        used_pat = re.compile(
            r"[Uu]sed.*?(\$[\d,]+\s*[-\u2013\u2014]\s*\$[\d,]+)",
            re.DOTALL,
        )
        m = used_pat.search(text)
        if m:
            result = parse_price_range(m.group(1))
            if result:
                log.info("A100 scraped price: $%.0f–$%.0f (mid $%.0f)", *result)
                return result

        # Wider fallback: any range near "A100" mentions
        result = parse_price_range(text)
        if result:
            log.info("A100 best-effort price: $%.0f–$%.0f (mid $%.0f)", *result)
            return result

    except Exception as exc:
        log.warning("A100 scrape failed: %s", exc)

    return None


def fetch_h100_price() -> Optional[Tuple[float, float, float]]:
    """Scrape JarvisLabs H100 blog for secondary-market price range."""
    url = "https://docs.jarvislabs.ai/blog/h100-price"
    log.info("Fetching H100 price from %s", url)
    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        text = soup.get_text(" ", strip=True)

        # Look for secondary / used market section
        sec_pat = re.compile(
            r"[Ss]econdary.*?(\$[\d,]+\s*[-\u2013\u2014]\s*\$[\d,]+)",
            re.DOTALL,
        )
        m = sec_pat.search(text)
        if m:
            result = parse_price_range(m.group(1))
            if result:
                log.info("H100 scraped price: $%.0f–$%.0f (mid $%.0f)", *result)
                return result

        used_pat = re.compile(
            r"[Uu]sed.*?(\$[\d,]+\s*[-\u2013\u2014]\s*\$[\d,]+)",
            re.DOTALL,
        )
        m = used_pat.search(text)
        if m:
            result = parse_price_range(m.group(1))
            if result:
                log.info("H100 used price: $%.0f–$%.0f (mid $%.0f)", *result)
                return result

    except Exception as exc:
        log.warning("H100 scrape failed: %s", exc)

    return None


# ─── Database ─────────────────────────────────────────────────────────────────

def get_db_connection():
    """Return a psycopg2 connection, retrying up to 5 times on failure."""
    for attempt in range(1, 6):
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
            )
            log.info("Database connected (attempt %d)", attempt)
            return conn
        except psycopg2.OperationalError as exc:
            log.warning("DB connect attempt %d failed: %s", attempt, exc)
            if attempt < 5:
                time.sleep(10 * attempt)
    raise RuntimeError("Could not connect to the database after 5 attempts")


INSERT_SQL = """
INSERT INTO gpu_market_prices
    (fetched_at, model, condition,
     price_low_usd, price_high_usd, price_mid_usd,
     original_cost_usd, source)
VALUES
    (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (fetched_at, model, condition) DO UPDATE
    SET price_low_usd     = EXCLUDED.price_low_usd,
        price_high_usd    = EXCLUDED.price_high_usd,
        price_mid_usd     = EXCLUDED.price_mid_usd,
        original_cost_usd = EXCLUDED.original_cost_usd,
        source            = EXCLUDED.source;
"""


def insert_price(conn, model: str, condition: str,
                 low: float, high: float, mid: float,
                 original_cost: float, source: str) -> None:
    fetched_at = datetime.utcnow()
    with conn.cursor() as cur:
        cur.execute(INSERT_SQL, (
            fetched_at, model, condition,
            low, high, mid,
            original_cost, source,
        ))
    conn.commit()
    log.info(
        "Inserted: %-30s  cond=%-10s  $%.0f–$%.0f (mid $%.0f)  src=%s",
        model, condition, low, high, mid, source,
    )


# ─── Main fetch cycle ─────────────────────────────────────────────────────────

def run_fetch_cycle(conn) -> None:
    log.info("=== Starting fetch cycle ===")
    now = datetime.utcnow().isoformat(timespec="seconds")

    # ── A100 ──────────────────────────────────────────────────────────────────
    a100_result = fetch_a100_price()
    fb_a100 = FALLBACK_PRICES["NVIDIA A100-SXM4-80GB"]

    if a100_result:
        lo, hi, mid = a100_result
        # Sanity-check: reject obviously wrong values
        if 1_000 <= lo <= 50_000 and 1_000 <= hi <= 50_000:
            insert_price(conn, "NVIDIA A100-SXM4-80GB", "used_good",
                         lo, hi, mid, fb_a100["original_cost_usd"], "web_scrape")
        else:
            log.warning("A100 scraped values out of range (lo=%.0f hi=%.0f) — using fallback", lo, hi)
            a100_result = None

    if not a100_result:
        insert_price(conn, "NVIDIA A100-SXM4-80GB", "used_good",
                     fb_a100["price_low_usd"], fb_a100["price_high_usd"],
                     fb_a100["price_mid_usd"], fb_a100["original_cost_usd"], "fallback")

    # ── H100 ──────────────────────────────────────────────────────────────────
    h100_result = fetch_h100_price()
    fb_h100 = FALLBACK_PRICES["NVIDIA H100-SXM5-80GB"]

    if h100_result:
        lo, hi, mid = h100_result
        if 5_000 <= lo <= 100_000 and 5_000 <= hi <= 100_000:
            insert_price(conn, "NVIDIA H100-SXM5-80GB", "used_good",
                         lo, hi, mid, fb_h100["original_cost_usd"], "web_scrape")
        else:
            log.warning("H100 scraped values out of range (lo=%.0f hi=%.0f) — using fallback", lo, hi)
            h100_result = None

    if not h100_result:
        insert_price(conn, "NVIDIA H100-SXM5-80GB", "used_good",
                     fb_h100["price_low_usd"], fb_h100["price_high_usd"],
                     fb_h100["price_mid_usd"], fb_h100["original_cost_usd"], "fallback")

    log.info("=== Fetch cycle complete — next run in %.1f hours ===", FETCH_INTERVAL_HRS)

    # Generate and store AI market commentary after each price fetch
    generate_market_commentary(conn)


# ─── AI Market Commentary ─────────────────────────────────────────────────────

def generate_market_commentary(conn) -> None:
    """
    Pulls live prices + fleet data from DB, asks Claude to write three sections
    of market intelligence, then stores them in gpu_market_commentary.
    Falls back silently if ANTHROPIC_API_KEY is not set.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        log.info("ANTHROPIC_API_KEY not set — skipping AI commentary")
        return

    log.info("Generating AI market commentary…")
    try:
        cursor = conn.cursor()

        # Current prices
        cursor.execute("""
            SELECT model, price_low_usd, price_high_usd, price_mid_usd, original_cost_usd, source
            FROM v_latest_market_prices WHERE condition = 'used_good' ORDER BY model
        """)
        prices = cursor.fetchall()

        # Fleet decision summary — query underlying table for full NPV columns
        cursor.execute("""
            WITH latest AS (
                SELECT DISTINCT ON (gpu_uuid)
                    gpu_uuid, decision, health_score, npv_sell, npv_keep
                FROM gpu_economic_decisions
                ORDER BY gpu_uuid, time DESC
            )
            SELECT decision, COUNT(*) as n,
                   ROUND(AVG(health_score)::numeric,1) as avg_health,
                   ROUND(AVG(npv_sell)::numeric,0)     as avg_sell,
                   ROUND(AVG(npv_keep)::numeric,0)     as avg_keep
            FROM latest GROUP BY decision ORDER BY n DESC
        """)
        decisions = cursor.fetchall()

        # Per-model breakdown
        cursor.execute("""
            WITH latest_dec AS (
                SELECT DISTINCT ON (gpu_uuid) gpu_uuid, decision
                FROM gpu_economic_decisions ORDER BY gpu_uuid, time DESC
            ),
            latest_health AS (
                SELECT DISTINCT ON (gpu_uuid) gpu_uuid, overall_score
                FROM gpu_health_scores ORDER BY gpu_uuid, time DESC
            )
            SELECT a.model, COUNT(*) as total,
                   SUM(CASE WHEN d.decision='sell'      THEN 1 ELSE 0 END) as sell_n,
                   SUM(CASE WHEN d.decision='keep'      THEN 1 ELSE 0 END) as keep_n,
                   SUM(CASE WHEN d.decision='repurpose' THEN 1 ELSE 0 END) as repur_n,
                   ROUND(AVG(h.overall_score)::numeric,1) as avg_health
            FROM gpu_assets a
            JOIN latest_dec d ON a.gpu_uuid = d.gpu_uuid
            JOIN latest_health h ON a.gpu_uuid = h.gpu_uuid
            GROUP BY a.model ORDER BY a.model
        """)
        model_rows = cursor.fetchall()

        price_txt = "\n".join(
            f"  {r[0]}: ${r[1]:,.0f}–${r[2]:,.0f} (mid ${r[3]:,.0f}), original ${r[4]:,.0f}, src={r[5]}"
            for r in prices
        ) or "  No price data yet."

        decision_txt = "\n".join(
            f"  {r[0].upper()}: {r[1]} GPU(s), avg health {r[2]}/100, avg NPV sell ${r[3]:,.0f}, keep ${r[4]:,.0f}"
            for r in decisions
        ) or "  No decision data yet."

        model_txt = "\n".join(
            f"  {r[0]}: {r[1]} units, avg health {r[5]}/100 [KEEP:{r[3]} SELL:{r[2]} REPURPOSE:{r[4]}]"
            for r in model_rows
        ) or "  No model data yet."

        prompt = f"""You are a GPU fleet economics analyst. Write exactly three short paragraphs for a live dashboard.

Live data ({datetime.utcnow().strftime('%d %b %Y %H:%M UTC')}):
Secondary market prices:
{price_txt}
Fleet decisions:
{decision_txt}
Model breakdown:
{model_txt}

Write three paragraphs, each 2-4 sentences. Plain text only — no markdown, no bullet points, no headings.
Paragraph 1: Current secondary market dynamics (reference the actual prices, Blackwell ramp, supply/demand).
Paragraph 2: What the fleet NPV data reveals — interpret the KEEP/SELL/REPURPOSE split and health scores.
Paragraph 3: Forward-looking view — what the operator should watch over the next 3–6 months.
Be commercially sharp and reference the specific numbers from the data above."""

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        full_text = message.content[0].text.strip()

        # Split into 3 paragraphs
        paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
        sections = ["market_dynamics", "fleet_analysis", "forward_view"]

        for i, section in enumerate(sections):
            content = paragraphs[i] if i < len(paragraphs) else paragraphs[-1] if paragraphs else "No data."
            cursor.execute("""
                INSERT INTO gpu_market_commentary (generated_at, section, content, model_used)
                VALUES (NOW(), %s, %s, %s)
                ON CONFLICT (generated_at, section) DO NOTHING
            """, (section, content, "claude-3-5-haiku-20241022"))

        conn.commit()
        log.info("AI commentary written to gpu_market_commentary (%d sections)", len(sections))

    except Exception as exc:
        log.error("Failed to generate AI commentary: %s", exc, exc_info=True)
        try:
            conn.rollback()
        except Exception:
            pass


# ─── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    log.info("Market Price Fetcher starting up")
    log.info("  DB: %s@%s:%s/%s", DB_USER, DB_HOST, DB_PORT, DB_NAME)
    log.info("  Interval: %.1f hours", FETCH_INTERVAL_HRS)

    conn = get_db_connection()

    while True:
        try:
            run_fetch_cycle(conn)
        except psycopg2.Error as exc:
            log.error("DB error during fetch cycle: %s — reconnecting", exc)
            try:
                conn.close()
            except Exception:
                pass
            conn = get_db_connection()
        except Exception as exc:
            log.error("Unexpected error during fetch cycle: %s", exc, exc_info=True)

        sleep_secs = FETCH_INTERVAL_HRS * 3600
        log.info("Sleeping for %.0f seconds…", sleep_secs)
        time.sleep(sleep_secs)


if __name__ == "__main__":
    main()
