# Service Account for the VM (Instance Profile equivalent)
resource "google_service_account" "vm_sa" {
  account_id   = "fbt-vm-sa"
  display_name = "Service Account for FBT VM"
}

# Static External IP (Elastic IP equivalent)
resource "google_compute_address" "static_ip" {
  name   = "fbt-static-ip"
  region = var.gcp_region
}

# The VM itself
resource "google_compute_instance" "app_server" {
  name         = "fbt-production-server"
  machine_type = "e2-small"
  zone         = var.gcp_zone
  tags         = ["ssh-server", "web-server"] # Applies the firewall rules

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 25 # GB, standard persistent disk is cheap
      type  = "pd-standard"
    }
  }

  network_interface {
    network    = google_compute_network.vpc_network.id
    subnetwork = google_compute_subnetwork.subnet.id
    access_config {
      nat_ip = google_compute_address.static_ip.address
    }
  }

  service_account {
    email  = google_service_account.vm_sa.email
    scopes = ["cloud-platform"]
  }

  metadata_startup_script = file("${path.module}/scripts/bootstrap.sh")

  # Ensure IP and Network exist first
  depends_on = [
    google_compute_address.static_ip,
    google_compute_subnetwork.subnet
  ]
}
