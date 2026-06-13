resource "random_id" "bucket_prefix" {
  byte_length = 8
}

# Cloud Storage Bucket for Postgres Backups (S3 equivalent here on GCP)
resource "google_storage_bucket" "db_backups" {
  name          = "fbt-backups-${random_id.bucket_prefix.hex}"
  location      = var.gcp_region
  force_destroy = true # Allows clean `terraform destroy` even if backups exist

  storage_class = "STANDARD"

  # Keep backups for 3 weeks, then delete them to save money
  lifecycle_rule {
    condition {
      age = 21
    }
    action {
      type = "Delete"
    }
  }
}

# Grant the VM's Service Account access to write to this bucket
resource "google_storage_bucket_iam_member" "vm_sa_bucket_access" {
  bucket = google_storage_bucket.db_backups.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.vm_sa.email}"
}
