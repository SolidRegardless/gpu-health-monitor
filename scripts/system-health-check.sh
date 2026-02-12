#!/bin/bash
# GPU Health Monitor - System Health Check
# Comprehensive diagnostic script to verify all components

set -e

cd "$(dirname "$0")/../docker"

echo "=================================="
echo "GPU Health Monitor - System Check"
echo "=================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

success() { echo -e "${GREEN}✓${NC} $1"; }
warning() { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; }

# 1. Check all services are running
echo "1. Checking Docker Services..."
echo "------------------------------"

EXPECTED_SERVICES=18
RUNNING_SERVICES=$(docker compose ps --filter "status=running" --format "{{.Name}}" | wc -l)

if [ "$RUNNING_SERVICES" -eq "$EXPECTED_SERVICES" ]; then
    success "All $EXPECTED_SERVICES services running"
else
    warning "$RUNNING_SERVICES/$EXPECTED_SERVICES services running"
fi

# List service status
docker compose ps --format "table {{.Name}}\t{{.Status}}" | head -20

echo ""

# 2. Check database connectivity
echo "2. Checking Database..."
echo "------------------------"

if docker compose exec timescaledb psql -U gpu_monitor -d gpu_health -c "SELECT 1" > /dev/null 2>&1; then
    success "Database connection OK"
else
    error "Database connection failed"
fi

echo ""

# 3. Check data tables
echo "3. Checking Data Tables..."
echo "--------------------------"

check_table() {
    TABLE=$1
    COUNT=$(docker compose exec -T timescaledb psql -U gpu_monitor -d gpu_health -t -c "SELECT COUNT(*) FROM $TABLE" 2>/dev/null | tr -d ' ')
    if [ -n "$COUNT" ] && [ "$COUNT" -gt 0 ]; then
        success "$TABLE: $COUNT rows"
    else
        warning "$TABLE: Empty or missing"
    fi
}

check_table "gpu_metrics"
check_table "gpu_health_scores"
check_table "gpu_features"
check_table "gpu_failure_predictions"
check_table "gpu_economic_decisions"
check_table "anomalies"

echo ""

# 4. Check Kafka topics
echo "4. Checking Kafka Topics..."
echo "---------------------------"

TOPICS=$(docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list 2>/dev/null | wc -l)
if [ "$TOPICS" -ge 4 ]; then
    success "Kafka topics: $TOPICS found"
    docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list 2>/dev/null | sed 's/^/  - /'
else
    warning "Kafka topics: Only $TOPICS found (expected 4+)"
fi

echo ""

# 5. Check service logs for errors
echo "5. Checking Service Logs..."
echo "---------------------------"

check_service_errors() {
    SERVICE=$1
    ERRORS=$(docker compose logs --tail=50 $SERVICE 2>/dev/null | grep -i "error\|exception\|failed" | wc -l)
    if [ "$ERRORS" -eq 0 ]; then
        success "$SERVICE: No errors"
    else
        warning "$SERVICE: $ERRORS error lines found"
    fi
}

check_service_errors "collector"
check_service_errors "health-scorer"
check_service_errors "feature-engineering"
check_service_errors "failure-predictor"
check_service_errors "economic-engine"
check_service_errors "ml-detector"

echo ""

# 6. Check API endpoints
echo "6. Checking API Endpoints..."
echo "----------------------------"

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    success "REST API responding"
else
    error "REST API not responding"
fi

if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
    success "Grafana responding"
else
    warning "Grafana not responding (may need login)"
fi

if curl -s http://localhost:5000/health > /dev/null 2>&1; then
    success "MLflow responding"
else
    warning "MLflow not responding"
fi

echo ""

# 7. Check data freshness
echo "7. Checking Data Freshness..."
echo "-----------------------------"

LATEST_METRIC=$(docker compose exec -T timescaledb psql -U gpu_monitor -d gpu_health -t -c "SELECT EXTRACT(EPOCH FROM (NOW() - MAX(time))) FROM gpu_metrics" 2>/dev/null | tr -d ' ')
if [ -n "$LATEST_METRIC" ]; then
    if [ $(echo "$LATEST_METRIC < 60" | bc) -eq 1 ]; then
        success "Latest metric: ${LATEST_METRIC}s ago (fresh)"
    else
        warning "Latest metric: ${LATEST_METRIC}s ago (stale)"
    fi
fi

LATEST_SCORE=$(docker compose exec -T timescaledb psql -U gpu_monitor -d gpu_health -t -c "SELECT EXTRACT(EPOCH FROM (NOW() - MAX(time))) FROM gpu_health_scores" 2>/dev/null | tr -d ' ')
if [ -n "$LATEST_SCORE" ]; then
    SCORE_MINS=$(echo "$LATEST_SCORE / 60" | bc)
    if [ $(echo "$LATEST_SCORE < 1800" | bc) -eq 1 ]; then
        success "Latest health score: ${SCORE_MINS}m ago"
    else
        warning "Latest health score: ${SCORE_MINS}m ago"
    fi
fi

echo ""

# 8. Check continuous aggregates
echo "8. Checking Continuous Aggregates..."
echo "-------------------------------------"

AGGREGATES=$(docker compose exec -T timescaledb psql -U gpu_monitor -d gpu_health -t -c "SELECT COUNT(*) FROM timescaledb_information.continuous_aggregates" 2>/dev/null | tr -d ' ')
if [ "$AGGREGATES" -eq 3 ]; then
    success "Continuous aggregates: $AGGREGATES/3"
else
    warning "Continuous aggregates: $AGGREGATES/3 (expected 3)"
fi

echo ""

# 9. Summary
echo "=================================="
echo "System Health Summary"
echo "=================================="

if [ "$RUNNING_SERVICES" -eq "$EXPECTED_SERVICES" ]; then
    echo -e "${GREEN}Status: Healthy ✓${NC}"
else
    echo -e "${YELLOW}Status: Partial (some services down)${NC}"
fi

echo ""
echo "Access Points:"
echo "  - Grafana:  http://localhost:3000"
echo "  - API:      http://localhost:8000"
echo "  - MLflow:   http://localhost:5000"
echo "  - Adminer:  http://localhost:8080"
echo ""
