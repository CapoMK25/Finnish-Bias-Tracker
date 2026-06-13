terraform {
  required_version = ">= 1.10.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # NOTE: To use GCS for remote state (like S3 backend without DynamoDB), 
  # uncomment this block after creating a bucket manually:
  # backend "gcs" {
  #   bucket  = "my-terraform-state-bucket"
  #   prefix  = "terraform/state"
  # }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
  zone    = var.gcp_zone
}
