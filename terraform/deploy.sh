#!/bin/bash
set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     GPU Health Monitor - Azure Deployment Script              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
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
echo "✅ Deployment complete!"
echo ""
echo "⏳ Services are starting up (allow ~5 minutes for full initialization)"
echo ""
