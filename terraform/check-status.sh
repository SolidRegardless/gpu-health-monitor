#!/bin/bash

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     GPU Health Monitor - Deployment Status Check              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")"

# Get the public IP from Terraform output
PUBLIC_IP=$(terraform output -raw public_ip 2>/dev/null)

if [ -z "$PUBLIC_IP" ]; then
    echo "❌ No deployment found. Run ./deploy.sh first."
    exit 1
fi

echo "🌐 Public IP: $PUBLIC_IP"
echo "🔗 Grafana URL: http://$PUBLIC_IP:3000"
echo ""

# Check if Grafana is responding
echo "🔍 Checking Grafana availability..."
if curl -s -o /dev/null -w "%{http_code}" "http://$PUBLIC_IP:3000" | grep -q "200\|302"; then
    echo "✅ Grafana is responding!"
else
    echo "⏳ Grafana not yet available (services may still be starting)"
fi

echo ""
echo "📊 To view full deployment info:"
echo "   terraform output deployment_info"
echo ""
echo "🔐 To SSH into the VM:"
echo "   ssh azureuser@$PUBLIC_IP"
echo ""
