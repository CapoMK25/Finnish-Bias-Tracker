# SSH Key
resource "hcloud_ssh_key" "deploy" {
  name       = "fbt-deploy-key"
  public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIE7VcqcxNz/3CJYZ9GIbXsirsvdc8xDZd92dcl0KrPSH capomk@archlinux"
}

# Firewall
resource "hcloud_firewall" "fbt" {
  name = "fbt-firewall"

  # SSH
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = ["0.0.0.0/0", "::/0"]  # TODO: restrict to your IP
  }

  # HTTP
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  # HTTPS
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  # Outbound: all (default, but explicit)
  rule {
    direction       = "out"
    protocol        = "tcp"
    port            = "any"
    destination_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction       = "out"
    protocol        = "udp"
    port            = "any"
    destination_ips = ["0.0.0.0/0", "::/0"]
  }
}

# Server
resource "hcloud_server" "fbt" {
  name        = "fbt-prod"
  image       = "debian-12"  # LTS, stable
  server_type = var.server_type
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.deploy.id]

  # Attach firewall
  firewall_ids = [hcloud_firewall.fbt.id]

  # User data (cloud-init) — replaces your bootstrap.sh
  user_data = templatefile("${path.module}/cloud-init.yml", {
    app_dir = "/opt/fbt"
  })
}