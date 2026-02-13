#!/bin/bash
set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     GPU Health Monitor - Azure Deployment Script              ║"
echo "║     Version: 1.0 (Production-Ready with All Fixes)            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📚 This deployment includes:"
echo "   ✅ All 13 gauge panels fixed across 4 dashboards"
echo "   ✅ Schema conflicts resolved (correct column names)"
echo "   ✅ 5-GPU simulation with distinct health profiles"
echo "   ✅ Complete data pipeline verification"
echo ""
echo "   📖 See CHANGELOG.md and GAUGE_FIX_SUMMARY.md for full details"
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Check prerequisites
echo "🔍 Checking prerequisites..."

if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found. Install: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform not found. Install: https://www.terraform.io/downloads"
    exit 1
fi

if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Run: az login"
    exit 1
fi

echo "✅ Prerequisites met"
echo ""

# Create archive
echo "📦 Creating deployment archive..."
cd ..
tar -czf terraform/gpu-health-monitor.tar.gz \
  --exclude='.git' \
  --exclude='terraform' \
  --exclude='*.md' \
  --exclude='docs' \
  --exclude='CLEANUP_COMPLETE.md' \
  --exclude='NEXT_STEPS.md' \
  --exclude='PRODUCTION_READY.md' \
  docker/ \
  schema/ \
  src/ \
  config/

echo "✅ Archive created ($(du -h terraform/gpu-health-monitor.tar.gz | cut -f1))"
echo "   Includes: Fixed dashboards + corrected schema + multi-GPU mock"
echo ""

# Deploy with Terraform
cd terraform

echo "🚀 Initializing Terraform..."
terraform init

echo ""
echo "📋 Planning deployment..."
terraform plan

echo ""
echo "🎯 Ready to deploy!"
echo ""
read -p "Deploy to Azure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Deployment cancelled"
    exit 0
fi

echo ""
echo "🚀 Deploying infrastructure..."
terraform apply -auto-approve

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║               Deployment Complete - What's Next?               ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║                                                                ║"
echo "║  1. Wait ~5 minutes for full stack initialization             ║"
echo "║  2. Get connection details: terraform output                   ║"
echo "║  3. Access Grafana at the displayed URL (admin/admin123)       ║"
echo "║  4. Check all 6 dashboards - all gauges should display         ║"
echo "║                                                                ║"
echo "║  Verification:                                                 ║"
echo "║  • SSH to VM and check: docker ps (17 containers running)     ║"
echo "║  • Query DB: docker exec timescaledb psql -U tsdb -d gpu...   ║"
echo "║  • View logs: docker logs -f gpu-health-monitor-collector-1   ║"
echo "║                                                                ║"
echo "║  📚 Documentation:                                             ║"
echo "║  • GAUGE_FIX_SUMMARY.md - Complete gauge fix details          ║"
echo "║  • CHANGELOG.md - Full change history                          ║"
echo "║  • FRESH_DEPLOYMENT.md - Fresh deployment guide                ║"
echo "║                                                                ║"
echo "║  🎯 To destroy: terraform destroy -auto-approve                ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
