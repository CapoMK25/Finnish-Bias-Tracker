output "server_ip" {
  description = "The public IP address of the FBT server"
  value       = google_compute_address.static_ip.address
}

output "backup_bucket_name" {
  description = "The name of the GCS bucket for Postgres backups"
  value       = google_storage_bucket.db_backups.name
}

output "dns_configuration_hint" {
  value = "Go to your domain registrar and point '${var.domain_name}' and 'api.${var.domain_name}' to ${google_compute_address.static_ip.address}"
}
