terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }

  # Local backend by default so this runs on a fresh clone with zero setup.
  # Switch to an S3 backend with state locking before using this for
  # anything beyond a personal demo, see known_limitations.md.
}

provider "aws" {
  region = var.aws_region
}
