variable "gcp_project_id" {
  description = "The GCP Project ID"
  type        = string
}

variable "gcp_region" {
  description = "The GCP Region (Hamina, Finland)"
  type        = string
  default     = "europe-north1"
}

variable "gcp_zone" {
  description = "The GCP Zone"
  type        = string
  default     = "europe-north1-a"
}

variable "domain_name" {
  description = "The domain name for the application (e.g., finnishbiastracker.fi)"
  type        = string
}
