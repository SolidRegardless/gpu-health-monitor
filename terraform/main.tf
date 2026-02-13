terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Resource Group
resource "azurerm_resource_group" "gpu_monitor" {
  name     = var.resource_group_name
  location = var.location
  
  tags = {
    Environment = "Demo"
    Project     = "GPU-Health-Monitor"
    ManagedBy   = "Terraform"
  }
}

# Virtual Network
resource "azurerm_virtual_network" "gpu_monitor" {
  name                = "${var.prefix}-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.gpu_monitor.location
  resource_group_name = azurerm_resource_group.gpu_monitor.name
  
  tags = azurerm_resource_group.gpu_monitor.tags
}

# Subnet
resource "azurerm_subnet" "gpu_monitor" {
  name                 = "${var.prefix}-subnet"
  resource_group_name  = azurerm_resource_group.gpu_monitor.name
  virtual_network_name = azurerm_virtual_network.gpu_monitor.name
  address_prefixes     = ["10.0.1.0/24"]
}

# Public IP
resource "azurerm_public_ip" "gpu_monitor" {
  name                = "${var.prefix}-public-ip"
  location            = azurerm_resource_group.gpu_monitor.location
  resource_group_name = azurerm_resource_group.gpu_monitor.name
  allocation_method   = "Static"
  sku                 = "Standard"
  
  tags = azurerm_resource_group.gpu_monitor.tags
}

# Network Security Group
resource "azurerm_network_security_group" "gpu_monitor" {
  name                = "${var.prefix}-nsg"
  location            = azurerm_resource_group.gpu_monitor.location
  resource_group_name = azurerm_resource_group.gpu_monitor.name
  
  # SSH access
  security_rule {
    name                       = "SSH"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
  
  # Grafana access
  security_rule {
    name                       = "Grafana"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "3000"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
  
  tags = azurerm_resource_group.gpu_monitor.tags
}

# Network Interface
resource "azurerm_network_interface" "gpu_monitor" {
  name                = "${var.prefix}-nic"
  location            = azurerm_resource_group.gpu_monitor.location
  resource_group_name = azurerm_resource_group.gpu_monitor.name
  
  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.gpu_monitor.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.gpu_monitor.id
  }
  
  tags = azurerm_resource_group.gpu_monitor.tags
}

# Associate NSG with NIC
resource "azurerm_network_interface_security_group_association" "gpu_monitor" {
  network_interface_id      = azurerm_network_interface.gpu_monitor.id
  network_security_group_id = azurerm_network_security_group.gpu_monitor.id
}

# Virtual Machine
resource "azurerm_linux_virtual_machine" "gpu_monitor" {
  name                = "${var.prefix}-vm"
  resource_group_name = azurerm_resource_group.gpu_monitor.name
  location            = azurerm_resource_group.gpu_monitor.location
  size                = var.vm_size
  admin_username      = var.admin_username
  
  network_interface_ids = [
    azurerm_network_interface.gpu_monitor.id,
  ]
  
  admin_ssh_key {
    username   = var.admin_username
    public_key = file(var.ssh_public_key_path)
  }
  
  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 64
  }
  
  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-noble"
    sku       = "24_04-lts-gen2"
    version   = "latest"
  }
  
  custom_data = base64encode(file("${path.module}/cloud-init-simple.yaml"))
  
  tags = azurerm_resource_group.gpu_monitor.tags
}
