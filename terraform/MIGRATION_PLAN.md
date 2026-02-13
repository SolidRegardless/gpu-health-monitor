# Migration to Terraform IaC

## Current State
- ✅ VM deallocated (stopped, no charges except storage)
- Manual resource group: GPU-HEALTH-MONITOR-RG
- Resources: VM, VNet, NSG, NIC, Public IP, Disk, SSH key

## Goal
Manage all Azure infrastructure with Terraform for:
- Version control and reproducibility
- Easy tear-down/rebuild
- Documentation as code
- Consistent deployments

## Approach: Clean Start (Recommended)

### Phase 1: Clean Up Manual Resources ✅ READY
1. Delete the manually-created resource group
   - This removes all resources at once (VM, networking, etc.)
   - Clean slate for Terraform to manage

### Phase 2: Terraform Setup (Step-by-Step)
1. **Initialize Terraform**
   ```bash
   cd ~/.openclaw/workspace/gpu-health-monitor/terraform
   terraform init
   ```

2. **Plan the deployment**
   ```bash
   terraform plan
   ```
   - Review what will be created
   - Verify configuration matches requirements

3. **Apply incrementally** (if issues arise)
   ```bash
   # Option 1: Apply everything
   terraform apply
   
   # Option 2: Apply specific resources first (troubleshooting)
   terraform apply -target=azurerm_resource_group.gpu_monitor
   terraform apply -target=azurerm_virtual_network.gpu_monitor
   # etc.
   ```

4. **Deploy application**
   ```bash
   # After VM is ready, deploy the application
   ./deploy-application.sh
   ```

### Phase 3: Verification
1. SSH access works
2. All containers running
3. Grafana accessible
4. 10 GPUs generating metrics

## Configuration Files

### Already Set Up ✅
- `main.tf` - Infrastructure definition
- `variables.tf` - Variable declarations
- `outputs.tf` - Output values (IP address, etc.)
- `terraform.tfvars` - Your specific values (git-ignored)
- `cloud-init-simple.yaml` - VM initialization (Docker only)

### Deployment Script (Separate)
Application deployment happens AFTER infrastructure is created:
- Use SCP to copy code to VM
- SSH to start docker-compose
- Update database schema
- Verify services

## Advantages of This Approach

1. **Clean state** - No import complications
2. **Documented** - All infrastructure in code
3. **Reproducible** - Can rebuild anytime
4. **Version controlled** - Track infrastructure changes
5. **Flexible** - Easy to modify (change VM size, region, etc.)

## Risk Mitigation

- Application data is not stored on VM (stateless containers)
- Database runs in container (no persistent data needed for demo)
- Configuration files are in git
- Can rebuild in ~10 minutes

## Ready to Proceed?

Current status:
- ✅ VM stopped (no compute charges)
- ✅ Terraform configuration ready
- ✅ SSH keys configured
- ⏸️ Waiting for confirmation to delete manual resource group

Next command to run:
```bash
# Delete manual resource group (frees up ~$0.10/day storage)
az group delete --name GPU-HEALTH-MONITOR-RG --yes --no-wait
```

Then proceed with Terraform setup.
