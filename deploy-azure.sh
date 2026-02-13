#!/bin/bash
set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     GPU Health Monitor - Azure Deployment (CLI)               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Configuration
LOCATION="uksouth"
RG_NAME="gpu-health-monitor-rg"
VM_NAME="gpu-monitor-vm"
VM_SIZE="Standard_D2s_v5"  # 2 vCPU, 8GB RAM - Azure's current default
ADMIN_USER="azureuser"
IMAGE="Canonical:0001-com-ubuntu-server-jammy:22_04-lts-gen2:latest"

echo "📍 Region: $LOCATION"
echo "💻 VM Size: $VM_SIZE"
echo ""

# Create resource group
echo "🏗️  Creating resource group..."
az group create \
  --name $RG_NAME \
  --location $LOCATION \
  --tags Environment=Demo Project=GPU-Health-Monitor \
  --output none

# Create VM with cloud-init
echo "🚀 Creating VM (this takes ~2 minutes)..."
az vm create \
  --resource-group $RG_NAME \
  --name $VM_NAME \
  --location $LOCATION \
  --size $VM_SIZE \
  --image $IMAGE \
  --admin-username $ADMIN_USER \
  --generate-ssh-keys \
  --public-ip-sku Standard \
  --custom-data ./terraform/cloud-init-simple.yaml \
  --output none

echo "✅ VM created!"
echo ""

# Get public IP
echo "🌐 Getting public IP..."
PUBLIC_IP=$(az vm show -d \
  --resource-group $RG_NAME \
  --name $VM_NAME \
  --query publicIps -o tsv)

echo "✅ Public IP: $PUBLIC_IP"
echo ""

# Open ports
echo "🔓 Opening firewall ports..."
az vm open-port \
  --resource-group $RG_NAME \
  --name $VM_NAME \
  --port 3000 \
  --priority 1001 \
  --output none

echo "✅ Port 3000 (Grafana) opened"
echo ""

# Wait for cloud-init to complete (Docker installation)
echo "⏳ Waiting for Docker installation (60 seconds)..."
sleep 60

# Create deployment archive
echo "📦 Creating deployment archive..."
cd $(dirname $0)
tar -czf /tmp/gpu-health-monitor-deploy.tar.gz \
  --exclude='.git' \
  --exclude='terraform' \
  --exclude='*.md' \
  --exclude='docs' \
  docker/ \
  schema/ \
  src/ \
  config/

echo "✅ Archive created"
echo ""

# Copy to VM
echo "📤 Copying application to VM..."
scp -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null \
  /tmp/gpu-health-monitor-deploy.tar.gz \
  $ADMIN_USER@$PUBLIC_IP:/tmp/

echo "✅ Application copied"
echo ""

# Deploy on VM
echo "🐳 Deploying Docker stack..."
ssh -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null \
  $ADMIN_USER@$PUBLIC_IP << 'EOF'
cd /opt/gpu-health-monitor
tar -xzf /tmp/gpu-health-monitor-deploy.tar.gz
rm /tmp/gpu-health-monitor-deploy.tar.gz

# Wait for Docker to be ready
echo "Waiting for Docker..."
for i in {1..30}; do
  if docker ps >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

# Start the stack
echo "Starting containers..."
docker-compose -f docker/docker-compose.yml up -d

echo "Deployment complete!"
EOF

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          GPU Health Monitor - Deployment Complete             ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║                                                                ║"
echo "║  Grafana Dashboard: http://$PUBLIC_IP:3000"
echo "║  Username: admin                                               ║"
echo "║  Password: admin                                               ║"
echo "║                                                                ║"
echo "║  SSH Access: ssh $ADMIN_USER@$PUBLIC_IP"
echo "║                                                                ║"
echo "║  Note: Services starting up, allow ~2 minutes                  ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "🎯 To destroy: az group delete --name $RG_NAME --yes --no-wait"
echo ""
