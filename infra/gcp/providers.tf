terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.35"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.35"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.10"
    }
  }

  # Remote state bucket - will be created via bootstrap script
  backend "gcs" {
    bucket = "genuine-park-487014-a7-tfstate"
    prefix = "landright/infra"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

data "google_client_config" "current" {}

data "google_project" "current" {
  project_id = var.project_id
}
