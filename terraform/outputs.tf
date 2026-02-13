output "public_ip" {
  description = "Public IP address of the VM"
  value       = azurerm_public_ip.gpu_monitor.ip_address
}

output "grafana_url" {
  description = "URL to access Grafana dashboard"
  value       = "http://${azurerm_public_ip.gpu_monitor.ip_address}:3000"
}

output "ssh_connection" {
  description = "SSH connection command"
  value       = "ssh ${var.admin_username}@${azurerm_public_ip.gpu_monitor.ip_address}"
}

output "grafana_credentials" {
  description = "Default Grafana login credentials"
  value = {
    username = "admin"
    password = "admin"
  }
}

output "deployment_info" {
  description = "Important deployment information"
  value = <<-EOT
  
  ╔════════════════════════════════════════════════════════════════╗
  ║          GPU Health Monitor - Deployment Complete             ║
  ╠════════════════════════════════════════════════════════════════╣
  ║                                                                ║
  ║  Grafana Dashboard: http://${azurerm_public_ip.gpu_monitor.ip_address}:3000               ║
  ║  Username: admin                                               ║
  ║  Password: admin                                               ║
  ║                                                                ║
  ║  SSH Access: ssh ${var.admin_username}@${azurerm_public_ip.gpu_monitor.ip_address}        ║
  ║                                                                ║
  ║  Note: Allow ~5 minutes for all services to fully start        ║
  ║                                                                ║
  ╚════════════════════════════════════════════════════════════════╝
  
  EOT
}
