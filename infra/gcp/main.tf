# Small, intentionally separate piece: an HTTP Cloud Function that accepts
# the same synthetic event shape as the AWS side and writes it into GCP
# Cloud Logging as structured entries. It does not talk to the AWS
# detector, this exists to genuinely exercise a second cloud provider
# rather than to extend the detection pipeline across clouds, see
# docs/architecture.md for the reasoning.

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

data "archive_file" "ingest_function" {
  type        = "zip"
  source_dir  = "${path.module}/function"
  output_path = "${path.module}/.build/ingest_function.zip"
}

resource "google_storage_bucket" "function_source" {
  name                        = "${var.gcp_project_id}-${var.project_name}-src"
  location                    = var.gcp_region
  uniform_bucket_level_access = true
  force_destroy               = true
}

resource "google_storage_bucket_object" "ingest_function_zip" {
  name   = "ingest-function-${data.archive_file.ingest_function.output_md5}.zip"
  bucket = google_storage_bucket.function_source.name
  source = data.archive_file.ingest_function.output_path
}

resource "google_service_account" "ingest_function" {
  account_id   = "${var.project_name}-ingest"
  display_name = "Synthetic log ingest function"
}

resource "google_project_iam_member" "ingest_function_log_writer" {
  project = var.gcp_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.ingest_function.email}"
}

resource "google_cloudfunctions2_function" "ingest" {
  name     = "${var.project_name}-ingest"
  location = var.gcp_region

  build_config {
    runtime     = "python312"
    entry_point = "ingest"
    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = google_storage_bucket_object.ingest_function_zip.name
      }
    }
  }

  service_config {
    max_instance_count   = 3
    available_memory     = "128Mi"
    timeout_seconds       = 30
    service_account_email = google_service_account.ingest_function.email
  }
}

output "ingest_function_url" {
  value = google_cloudfunctions2_function.ingest.url
}
