variable "gcp_project_id" {
  description = "GCP project ID to deploy into"
  type        = string
}

variable "gcp_region" {
  description = "GCP region for the Cloud Function and staging bucket"
  type        = string
  default     = "us-central1"
}

variable "project_name" {
  description = "Prefix applied to resource names"
  type        = string
  default     = "cloud-log-monitor"
}
