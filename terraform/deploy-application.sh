#!/bin/bash
# Deploy GPU Health Monitor application to Terraform-managed VM

set -e

echo "=================================================="
echo "GPU Health Monitor - Application Deployment"
echo "=================================================="

# Get VM IP from Terraform output
VM_IP=$(terraform output -raw vm_public_ip 2>/dev/null)
if [ -z "$VM_IP" ]; then
    echo "❌ Error: Could not get VM IP from Terraform output"
    echo "   Run 'terraform apply' first"
    exit 1
fi

SSH_KEY=~/.ssh/azure-gpu-monitor-key
SSH_USER=azureuser

echo "Target VM: $VM_IP"
echo "SSH Key: $SSH_KEY"
echo ""

# Wait for SSH to be ready
echo "⏳ Waiting for SSH to be ready..."
for i in {1..30}; do
    if ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$SSH_USER@$VM_IP" "echo 'SSH ready'" &>/dev/null; then
        echo "✅ SSH is ready!"
        break
    fi
    echo "   Attempt $i/30... (waiting 10s)"
    sleep 10
done

# Wait for cloud-init to finish
echo ""
echo "⏳ Waiting for cloud-init to complete..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$VM_IP" \
    "cloud-init status --wait" || echo "⚠️  cloud-init check failed (might be okay)"

# Verify Docker is installed
echo ""
echo "🔍 Verifying Docker installation..."
ssh -i "$SSH_KEY" "$SSH_USER@$VM_IP" "docker --version && docker-compose --version"

# Create deployment archive
echo ""
echo "📦 Creating deployment archive..."
cd ~/.openclaw/workspace/gpu-health-monitor
tar czf /tmp/gpu-health-monitor.tar.gz \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='node_modules' \
    --exclude='*.log' \
    --exclude='terraform/.terraform' \
    --exclude='terraform/*.tfstate*' \
    docker/ \
    src/ \
    config/ \
    schema/ \
    services/

echo "✅ Archive created: $(du -h /tmp/gpu-health-monitor.tar.gz | cut -f1)"

# Copy to VM
echo ""
echo "📤 Uploading application to VM..."
scp -i "$SSH_KEY" /tmp/gpu-health-monitor.tar.gz "$SSH_USER@$VM_IP:/tmp/"

# Extract and deploy
echo ""
echo "🚀 Deploying application..."
ssh -i "$SSH_KEY" "$SSH_USER@$VM_IP" bash <<'ENDSSH'
    set -e
    
    # Extract archive
    sudo rm -rf /opt/gpu-health-monitor
    sudo mkdir -p /opt/gpu-health-monitor
    sudo tar xzf /tmp/gpu-health-monitor.tar.gz -C /opt/gpu-health-monitor
    sudo chown -R azureuser:azureuser /opt/gpu-health-monitor
    
    # Start services
    cd /opt/gpu-health-monitor/docker
    docker-compose down -v 2>/dev/null || true
    docker-compose up -d
    
    echo ""
    echo "⏳ Waiting for containers to start..."
    sleep 15
    
    # Check container status
    docker-compose ps
ENDSSH

echo ""
echo "=================================================="
echo "✅ Deployment Complete!"
echo "=================================================="
echo ""
echo "Grafana: http://$VM_IP:3000 (admin/admin)"
echo "SSH: ssh -i $SSH_KEY $SSH_USER@$VM_IP"
echo ""
echo "Next steps:"
echo "  1. Wait 2-3 minutes for all services to initialize"
echo "  2. Check logs: ssh -i $SSH_KEY $SSH_USER@$VM_IP 'cd /opt/gpu-health-monitor/docker && docker-compose logs -f'"
echo "  3. Verify: http://$VM_IP:3000"
echo ""
