terraform {
  required_version = ">= 1.5"
  
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
  }
}


variable "ssh_public_key_path" {
  description = "Path to your SSH public key"
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

variable "location" {
  description = "Hetzner datacenter location"
  type        = string
  default     = "hel1"  # Helsinki
}

variable "server_type" {
  description = "Hetzner server type"
  type        = string
  default     = "cx23"  # Hetzner CX23
}

provider "hcloud" {

}