# Grafana Credentials Management

## Security Best Practices

This deployment no longer uses default `admin:admin` credentials. Instead, Terraform generates a secure random password automatically.

## How It Works

### Automatic Password Generation (Default)

By default, Terraform will generate a 24-character random password for Grafana:

```bash
terraform apply
```

After deployment, retrieve the credentials:

```bash
terraform output grafana_credentials
```

Output:
```
{
  "password" = "x7!Kp2#mN9@qR5$wL8^tY3&hF6"
  "username" = "admin"
}
```

### Custom Password (Optional)

If you prefer to set your own password, add it to `terraform.tfvars`:

```hcl
grafana_admin_password = "YourSecurePassword123!"
```

Or pass it via command line:

```bash
terraform apply -var="grafana_admin_password=YourSecurePassword123!"
```

### Environment Variables

For CI/CD pipelines:

```bash
export TF_VAR_grafana_admin_password="YourSecurePassword123!"
terraform apply
```

## Viewing Credentials After Deployment

The credentials are marked as sensitive and won't appear in normal output.

To view them:

```bash
# Full credentials
terraform output grafana_credentials

# Just the password
terraform output -json grafana_credentials | jq -r '.password'

# Or via SSH on the deployed VM
ssh azureuser@<VM_IP>
cat /opt/gpu-health-monitor/docker/.env
```

## Security Notes

1. **Never commit `terraform.tfvars` with passwords** - It's already in `.gitignore`
2. **The `.env` file on the VM** contains the credentials with 600 permissions
3. **Rotate passwords regularly** by updating the variable and running `terraform apply`
4. **For production**, consider using Azure Key Vault:
   - Store password in Key Vault
   - Reference it via Terraform data source
   - Enable auto-rotation

## Changing Password After Deployment

If you need to change the Grafana password after deployment:

```bash
# Update terraform.tfvars or set TF_VAR_grafana_admin_password
terraform apply

# Or manually on the VM:
ssh azureuser@<VM_IP>
cd /opt/gpu-health-monitor/docker
echo "GRAFANA_ADMIN_PASSWORD=NewPassword123" >> .env
sudo docker-compose restart grafana
```

## Troubleshooting

### Can't log in with generated password

Check the actual password being used:

```bash
terraform output -raw grafana_credentials
```

### Need to reset password

Redeploy the Grafana container:

```bash
ssh azureuser@<VM_IP>
cd /opt/gpu-health-monitor/docker
sudo docker-compose stop grafana
sudo docker-compose rm -f grafana
# Update .env with new password
sudo docker-compose up -d grafana
```
