# Custom VPC
resource "google_compute_network" "vpc_network" {
  name                    = "fbt-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "fbt-subnet-eu-north1"
  ip_cidr_range = "10.0.1.0/24"
  region        = var.gcp_region
  network       = google_compute_network.vpc_network.id
}

# Allow SSH from anywhere (should be restricted in production later on)
resource "google_compute_firewall" "allow_ssh" {
  name    = "fbt-allow-ssh"
  network = google_compute_network.vpc_network.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
  source_ranges = ["0.0.0.0/0"] 
  target_tags   = ["ssh-server"]
}

# Allow HTTP/HTTPS traffic 
resource "google_compute_firewall" "allow_web" {
  name    = "fbt-allow-web"
  network = google_compute_network.vpc_network.name

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }
  # Note: In a production setup, restrict this strictly to Cloudflare IP ranges
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["web-server"]
}
