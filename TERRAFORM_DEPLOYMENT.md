# Terraform Azure Deployment

**One-command cloud deployment for GPU Health Monitor**

## What's Included

Complete Infrastructure-as-Code deployment:

- **Azure VM** (Standard_D4s_v3: 4 vCPU, 16GB RAM)
- **Networking** (VNet, Public IP, NSG with ports 22 + 3000)
- **Automated Setup** (Docker installation via cloud-init)
- **Complete Stack** (Kafka, TimescaleDB, Grafana, 5-GPU simulation)
- **Production Ready** (Auto-provisioned dashboards, schema, mock data)

## Location

**East US** - Good latency for global demos (sub-100ms to UK, reasonable worldwide)

## Quick Deploy

```bash
cd terraform
./deploy.sh
```

That's it! In ~5 minutes you'll have a live URL.

## What Happens

1. **Terraform** provisions Azure resources (VM, networking, storage)
2. **Cloud-init** runs on first boot:
   - Installs Docker & Docker Compose
   - Extracts application archive
   - Launches all containers
   - Waits for services to be healthy
3. **Auto-provisioning** creates:
   - 16 database tables with proper schema
   - 5 GPU simulation with distinct health profiles
   - 6 Grafana dashboards (Fleet Overview, GPU Detail, Predictive, etc.)
   - Datacenter mapping (DC-EAST-01, 3 racks, 5 GPUs)

## Cost

**~$140/month** (~$0.192/hour) for Standard_D4s_v3

**Optimize costs:**
```bash
# Destroy when not needed
./destroy.sh

# Redeploy in 5 minutes when needed
./deploy.sh
```

## Access

After deployment:
```bash
# Get the Grafana URL
terraform output grafana_url
# Output: http://<public-ip>:3000

# Default credentials
# Username: admin
# Password: admin (change on first login)
```

## Files Created

```
terraform/
├── main.tf              # Azure resources (VM, networking, etc.)
├── variables.tf         # Configurable values (region, VM size, etc.)
├── outputs.tf           # Return values (IP, URL, SSH command)
├── cloud-init.yaml      # Automated setup script
├── README.md            # Detailed documentation
├── .gitignore           # Ignore state files and secrets
├── deploy.sh            # One-command deployment script
├── destroy.sh           # Clean up resources
└── check-status.sh      # Verify deployment status
```

## Customization

Edit `variables.tf` or pass command-line overrides:

```bash
# Different VM size
terraform apply -var="vm_size=Standard_D2s_v3"

# Different region
terraform apply -var="location=westus2"

# Custom SSH key
terraform apply -var="ssh_public_key_path=/path/to/key.pub"
```

## For Your Interview

**What to say:**

> "I've built a production-grade GPU monitoring system with complete infrastructure-as-code deployment. Let me show you..."
> 
> *(Open Grafana dashboard)* "This is monitoring 5 GPUs with distinct health profiles - here's GPU-mno345pqr678 showing aging symptoms with elevated ECC errors."
>
> "The entire stack - Kafka, TimescaleDB, Grafana, mock DCGM - deploys to Azure with a single Terraform command. From zero to live dashboard in 5 minutes."
>
> "The system simulates realistic GPU degradation patterns and uses ML to predict failures 7-90 days in advance."

**Why this impresses:**

✅ **DevOps maturity** - IaC, automated deployment, cloud-native  
✅ **Production thinking** - Not just code, but deployable infrastructure  
✅ **Visual impact** - Live, interactive dashboards they can explore  
✅ **Technical depth** - Complete data pipeline (DCGM → Kafka → DB → ML → Viz)  
✅ **Scalability story** - "This is 5 GPUs. Architecture scales to 10,000+."

## Troubleshooting

**Services not ready after 5 minutes?**
```bash
# SSH to the VM
ssh azureuser@<public-ip>

# Check cloud-init progress
tail -f /var/log/cloud-init-output.log

# Check deployment log
cat /var/log/gpu-monitor-deploy.log

# Check container status
cd /opt/gpu-health-monitor
docker-compose -f docker/docker-compose.yml ps
```

**Need to restart services?**
```bash
ssh azureuser@<public-ip>
cd /opt/gpu-health-monitor
docker-compose -f docker/docker-compose.yml restart
```

## Clean Up

When demo is done:
```bash
cd terraform
./destroy.sh
```

All resources deleted, zero monthly cost.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Azure East US                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Standard_D4s_v3 VM (Ubuntu 22.04 LTS)          │  │
│  │  ├─ Docker Engine                                │  │
│  │  ├─ Docker Compose                               │  │
│  │  └─ Auto-provisioned via cloud-init              │  │
│  │                                                   │  │
│  │  Running Containers:                             │  │
│  │  ├─ Zookeeper                                    │  │
│  │  ├─ Kafka                                        │  │
│  │  ├─ TimescaleDB (16 tables, hypertables)        │  │
│  │  ├─ Grafana (6 dashboards)                      │  │
│  │  ├─ Mock DCGM (5 GPU simulation)                │  │
│  │  ├─ Collector                                    │  │
│  │  ├─ Kafka Validator                             │  │
│  │  ├─ Kafka Enricher                              │  │
│  │  └─ Kafka Sink                                  │  │
│  └──────────────────────────────────────────────────┘  │
│             ↓                                           │
│      Public IP: x.x.x.x                                │
│      Port 3000: Grafana (NSG allow)                    │
│      Port 22: SSH (NSG allow)                          │
└─────────────────────────────────────────────────────────┘
                      ↓
            http://x.x.x.x:3000
         (Accessible worldwide)
```

## Next Steps

1. **Deploy**: Run `./deploy.sh`
2. **Access**: Open the Grafana URL in your browser
3. **Explore**: Navigate through the 6 dashboards
4. **Demo**: Walk through GPU health trends, failure predictions
5. **Impress**: Show the interviewer live, production-grade monitoring

Good luck with the interview! 🎯
