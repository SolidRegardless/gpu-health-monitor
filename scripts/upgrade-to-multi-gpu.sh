#!/bin/bash
# Multi-GPU Upgrade Script
# Stops current system, rebuilds with multi-GPU support, initializes database

set -e

echo "======================================================================"
echo "GPU Health Monitor - Multi-GPU Upgrade"
echo "======================================================================"
echo ""
echo "This will:"
echo "  - Stop all services"
echo "  - Rebuild mock-dcgm with 5-GPU support"
echo "  - Add 5 GPU assets to database"
echo "  - Restart all services"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

cd "$(dirname "$0")/../docker"

echo ""
echo "Step 1/5: Stopping services..."
docker compose down

echo ""
echo "Step 2/5: Rebuilding mock-dcgm with multi-GPU support..."
docker compose build mock-dcgm

echo ""
echo "Step 3/5: Starting database..."
docker compose up -d timescaledb zookeeper kafka
sleep 10

echo ""
echo "Step 4/5: Initializing multi-GPU assets..."
docker compose exec -T timescaledb psql -U gpu_monitor -d gpu_health < ../schema/01_init_schema_multi_gpu.sql

echo ""
echo "Step 5/5: Starting all services..."
docker compose up -d

echo ""
echo "Waiting for services to be ready..."
sleep 15

echo ""
echo "======================================================================"
echo "Multi-GPU Upgrade Complete!"
echo "======================================================================"
echo ""
echo "System now monitoring 5 GPUs:"
echo "  GPU 0 (GPU-abc123def456): Healthy - 6 months old"
echo "  GPU 1 (GPU-def456abc789): High temp - 18 months old"  
echo "  GPU 2 (GPU-ghi789jkl012): H100, Power hungry - 3 months old"
echo "  GPU 3 (GPU-mno345pqr678): Aging - 36 months old, ECC errors"
echo "  GPU 4 (GPU-stu901vwx234): H100, Excellent - 1 month old"
echo ""
echo "Endpoints:"
echo "  - Mock DCGM: http://localhost:9400/metrics"
echo "  - Grafana:   http://localhost:3000 (admin/admin)"
echo "  - API:       http://localhost:8000/docs"
echo ""
echo "Check status:"
echo "  docker compose ps"
echo "  docker compose logs -f mock-dcgm"
echo "  curl http://localhost:9400/health | jq"
echo ""
