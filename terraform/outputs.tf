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
  description = "Grafana login credentials"
  sensitive   = true
  value = {
    username = var.grafana_admin_user
    password = local.grafana_password
  }
}

output "api_url" {
  description = "URL to access API"
  value       = "http://${azurerm_public_ip.gpu_monitor.ip_address}:8000"
}

output "mlflow_url" {
  description = "URL to access MLflow"
  value       = "http://${azurerm_public_ip.gpu_monitor.ip_address}:5000"
}

output "adminer_url" {
  description = "URL to access Adminer (DB GUI)"
  value       = "http://${azurerm_public_ip.gpu_monitor.ip_address}:8080"
}

output "deployment_info" {
  description = "Important deployment information"
  value       = <<-EOT
  
  ╔══════════════════════════════════════════════════════════════════╗
  ║          GPU Health Monitor - Deployment Complete               ║
  ╠══════════════════════════════════════════════════════════════════╣
  ║                                                                  ║
  ║  🎯 Services:                                                    ║
  ║     Grafana:  http://${azurerm_public_ip.gpu_monitor.ip_address}:3000                                    ║
  ║     API:      http://${azurerm_public_ip.gpu_monitor.ip_address}:8000                                ║
  ║     MLflow:   http://${azurerm_public_ip.gpu_monitor.ip_address}:5000                                ║
  ║     Adminer:  http://${azurerm_public_ip.gpu_monitor.ip_address}:8080 (DB GUI)                       ║
  ║                                                                  ║
  ║  🔐 SSH: ssh ${var.admin_username}@${azurerm_public_ip.gpu_monitor.ip_address}                         ║
  ║                                                                  ║
  ║  💾 Database: TimescaleDB                                        ║
  ║     Host: ${azurerm_public_ip.gpu_monitor.ip_address}:5432                                 ║
  ║     DB: gpu_health / User: gpu_monitor                           ║
  ║                                                                  ║
  ║  ⚙️  Components Running:                                         ║
  ║     • Mock DCGM (GPU simulator)                                  ║
  ║     • Kafka + Zookeeper (streaming)                              ║
  ║     • Metric processors (validate/enrich/sink)                   ║
  ║     • ML models (anomaly detection, failure prediction)          ║
  ║     • Health scoring & alerting                                  ║
  ║                                                                  ║
  ║  🔐 Credentials:                                                 ║
  ║     Run: terraform output grafana_credentials                    ║
  ║                                                                  ║
  ╚══════════════════════════════════════════════════════════════════╝
  
  EOT
}
