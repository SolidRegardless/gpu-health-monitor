# GPU Health Monitor - Azure Terraform Deployment

Complete one-command deployment of the GPU Health Monitor to Azure East US.

## Prerequisites

1. **Azure CLI** installed and authenticated:
   ```bash
   az login
   ```

2. **Terraform** installed (v1.0+):
   ```bash
   # macOS
   brew install terraform
   
   # Ubuntu/Debian
   wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
   echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
   sudo apt update && sudo apt install terraform
   ```

3. **SSH Key** (will be used for VM access):
   ```bash
   # If you don't have one, generate it:
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa
   ```

## Quick Start

### 1. Prepare the Archive

From the project root:
```bash
# Create a tarball of the project (excluding unnecessary files)
tar -czf terraform/gpu-health-monitor.tar.gz \
  --exclude='.git' \
  --exclude='terraform' \
  --exclude='*.md' \
  --exclude='docs' \
  docker/ \
  schema/ \
  src/ \
  config/
```

### 2. Deploy to Azure

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Type `yes` when prompted.

### 3. Access Your Dashboard

After ~5 minutes, Terraform will output:
- **Grafana URL**: `http://<public-ip>:3000`
- **Credentials**: admin / admin
- **SSH Access**: `ssh azureuser@<public-ip>`

## Customization

Edit `variables.tf` or override via command line:

```bash
# Use a different VM size
terraform apply -var="vm_size=Standard_D2s_v3"

# Deploy to a different region
terraform apply -var="location=westus2"

# Use a custom SSH key
terraform apply -var="ssh_public_key_path=/path/to/your/key.pub"
```

## Cost Estimation

**Standard_D4s_v3** (4 vCPU, 16 GB RAM):
- ~$140/month (~$0.192/hour)
- East US region

**To minimize costs during demo:**
```bash
# Destroy when not in use
terraform destroy

# Redeploy when needed (5 minutes)
terraform apply
```

## Verify Deployment

SSH into the VM:
```bash
ssh azureuser@<public-ip>
```

Check service status:
```bash
cd /opt/gpu-health-monitor
docker-compose -f docker/docker-compose.yml ps
```

View logs:
```bash
docker-compose -f docker/docker-compose.yml logs -f
```

## Troubleshooting

**Services not starting?**
```bash
# Check cloud-init progress
tail -f /var/log/cloud-init-output.log

# Check deployment log
cat /var/log/gpu-monitor-deploy.log
```

**Grafana not accessible?**
- Verify NSG rules allow port 3000
- Check Grafana container: `docker logs gpu-health-monitor-grafana-1`

**Need to redeploy?**
```bash
# SSH to VM
ssh azureuser@<public-ip>

# Restart stack
cd /opt/gpu-health-monitor
docker-compose -f docker/docker-compose.yml down
docker-compose -f docker/docker-compose.yml up -d
```

## Clean Up

When you're done with the demo:
```bash
terraform destroy
```

Type `yes` to confirm. All Azure resources will be deleted.

## Architecture

- **Location**: East US (us-east-1)
- **VM**: Ubuntu 22.04 LTS
- **Networking**: VNet with public IP and NSG
- **Deployment**: Automated via cloud-init
- **Stack**: Docker Compose (Kafka, TimescaleDB, Grafana, Mock DCGM)

## Security Notes

- SSH and Grafana ports are open to `0.0.0.0/0` for demo purposes
- For production, restrict source IPs in NSG rules
- Change Grafana admin password after first login
- Consider using Azure Key Vault for secrets
