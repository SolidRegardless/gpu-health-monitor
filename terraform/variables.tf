variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
  default     = "gpu-health-monitor-rg"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "westus2"
}

variable "prefix" {
  description = "Prefix for resource names"
  type        = string
  default     = "gpu-monitor"
}

variable "vm_size" {
  description = "Azure VM size"
  type        = string
  default     = "Standard_B4ms" # 4 vCPU, 16 GB RAM, burstable
}

variable "admin_username" {
  description = "Admin username for the VM"
  type        = string
  default     = "azureuser"
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key file"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "ssh_private_key_path" {
  description = "Path to SSH private key file (for provisioners)"
  type        = string
  default     = "~/.ssh/id_rsa"
}
