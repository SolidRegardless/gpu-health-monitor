# Deployment Scripts Reference

This project includes two deployment scripts for Azure. Both deploy the **same production-ready system** with all gauge fixes and schema corrections applied.

## Quick Reference

| Script | Method | Best For | Prerequisites |
|--------|--------|----------|---------------|
| `deploy-azure.sh` | Azure CLI only | Quick demos, testing | Azure CLI + ssh keys |
| `terraform/deploy.sh` | Terraform + Azure CLI | Production, IaC workflows | Terraform + Azure CLI |

## Scripts

### 1. `deploy-azure.sh` - Simple Azure CLI Deployment

**Use when**: You want the fastest path to a running system.

```bash
./deploy-azure.sh
```

**What it does**:
- Creates VM using `az vm create` with cloud-init
- Copies application via SCP
- Starts Docker stack remotely via SSH
- Takes ~3-4 minutes total

**Prerequisites**:
- Azure CLI (`az`) installed and logged in
- SSH keys in `~/.ssh/` (generated automatically if missing)

**Pros**:
- Fastest deployment
- Minimal dependencies
- Easy to understand

**Cons**:
- No infrastructure-as-code tracking
- Manual resource management
- Less suitable for team environments

---

### 2. `terraform/deploy.sh` - Terraform Deployment

**Use when**: You want infrastructure-as-code and reproducible deployments.

```bash
cd terraform
./deploy.sh
```

**What it does**:
- Creates deployment archive
- Initializes Terraform
- Plans infrastructure changes
- Applies Terraform configuration
- Deploys via cloud-init automation

**Prerequisites**:
- Terraform installed (`terraform`)
- Azure CLI installed and logged in (`az`)

**Pros**:
- Infrastructure-as-code (version controlled)
- Repeatable deployments
- State management
- Better for production/team use

**Cons**:
- Additional tool dependency
- Slightly longer first-run time

---

## What's Deployed (Both Methods)

✅ **5-GPU Simulation** with distinct health profiles:
- GPU-abc123def456: healthy (A100, 6 months old)
- GPU-def456abc789: high_temp (A100, 18 months)
- GPU-ghi789jkl012: power_hungry (H100, 3 months)
- GPU-mno345pqr678: aging (A100, 36 months)
- GPU-stu901vwx234: excellent (H100, 1 month)

✅ **6 Grafana Dashboards** with all gauge fixes:
- GPU Fleet Overview
- GPU Overview
- GPU Detail
- GPU Predictive Health
- Datacenter Overview
- GPU Overview (Simple)

✅ **Complete Stack** (17 containers):
- Zookeeper + Kafka (event streaming)
- TimescaleDB (metrics storage)
- Mock DCGM (GPU data generation)
- Collector, Enricher, Sink (data pipeline)
- ML Training Service + API
- Grafana (visualization)
- + supporting services

✅ **All Recent Fixes Applied**:
- Schema conflicts resolved (`07_init_multi_gpu_data.sql`)
- All 13 gauge panels fixed across 4 dashboards
- Data pipeline verified (136+ metrics flowing)
- See `CHANGELOG.md` for complete history

---

## After Deployment

Both scripts output connection details:

```
Grafana Dashboard: http://<PUBLIC_IP>:3000
Username: admin
Password: admin123

SSH Access: ssh azureuser@<PUBLIC_IP>
```

**Verification Steps**:

1. **Wait 2-5 minutes** for services to initialize
2. **Access Grafana** at the URL (admin/admin123)
3. **Check dashboards**:
   - Open "GPU Fleet Overview"
   - Verify all 6 gauge panels show filled bars
   - Check "Datacenter Overview" - gauges should display
4. **Verify data flow** (via SSH):
   ```bash
   # Check containers
   docker ps  # Should show 17 running
   
   # Check metrics
   docker exec timescaledb psql -U tsdb -d gpu_health -c \
     "SELECT COUNT(*) FROM gpu_metrics;"
   ```

**Expected Results**:
- 17 containers running
- 100+ metrics in database (grows over time)
- All gauge panels displaying with filled progress bars
- Line charts showing 5 distinct GPU traces

---

## Destroying Resources

**Azure CLI method**:
```bash
az group delete --name gpu-health-monitor-rg --yes --no-wait
```

**Terraform method**:
```bash
cd terraform
terraform destroy -auto-approve
```

**Cost Note**: The deployed VM (Standard_D2s_v5 or Standard_B2ms) costs ~$0.10-0.15/hour. Always destroy resources after demos to avoid charges.

---

## Troubleshooting

### Deployment Fails with "Capacity not available"

**Solution**: Edit the script to use a different region:

```bash
# deploy-azure.sh
LOCATION="northeurope"  # or "eastus", "westeurope"

# terraform/main.tf
variable "location" {
  default = "northeurope"  # or other region
}
```

Regions with good capacity: `northeurope`, `westeurope`, `eastus2`, `westus2`

### Services Not Starting

**Check cloud-init logs** (SSH to VM):
```bash
sudo tail -f /var/log/cloud-init-output.log
```

### Gauges Not Displaying

**This is already fixed** in the current deployment. If you see empty gauges:
1. Verify you're using the latest code (check `git log`)
2. Ensure schema loaded correctly:
   ```bash
   docker logs timescaledb | grep -i error
   ```
3. Check metrics are flowing:
   ```bash
   docker logs gpu-health-monitor-collector-1
   ```

---

## Documentation References

- **GAUGE_FIX_SUMMARY.md** - Complete gauge fix details
- **CHANGELOG.md** - Full change history
- **FRESH_DEPLOYMENT.md** - Manual deployment guide
- **TERRAFORM_DEPLOYMENT.md** - Terraform-specific guide
- **INTERVIEW_DEMO_GUIDE.md** - Demo walkthrough

---

## Which Should I Use?

**For quick demos/testing**: Use `deploy-azure.sh`
- Fastest path to working system
- Minimal setup
- Easy cleanup

**For production/teams**: Use `terraform/deploy.sh`
- Version-controlled infrastructure
- Repeatable deployments
- Better change tracking
- Shows DevOps maturity in interviews

**Both are production-ready** with all fixes applied. Choose based on your use case.

---

_Last updated: 2026-02-13 - After comprehensive gauge fixes and schema corrections_
