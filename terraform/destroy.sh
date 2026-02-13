#!/bin/bash
set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     GPU Health Monitor - Destroy Azure Resources              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")"

echo "⚠️  This will destroy ALL Azure resources for the GPU Health Monitor"
echo ""
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Destruction cancelled"
    exit 0
fi

echo ""
echo "🗑️  Destroying infrastructure..."
terraform destroy -auto-approve

echo ""
echo "✅ All resources destroyed"
echo ""
