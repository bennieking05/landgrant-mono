# ------------------------------------------------------------------------------
# LandRight GCP Infrastructure - Testing Configuration
# Uses lowest-cost tiers suitable for development/testing
# ------------------------------------------------------------------------------

locals {
  common_labels = {
    app         = "landright"
    environment = var.environment
    managed_by  = "terraform"
  }
}

# ------------------------------------------------------------------------------
# Networking - VPC for private resources
# ------------------------------------------------------------------------------
resource "google_compute_network" "vpc" {
  name                    = "landright-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
  description             = "VPC for LandRight private resources"
  project                 = var.project_id

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_compute_subnetwork" "workloads" {
  name                     = "landright-workloads"
  ip_cidr_range            = var.subnet_cidr
  region                   = var.region
  network                  = google_compute_network.vpc.id
  private_ip_google_access = true
  project                  = var.project_id
}

# Private IP range for Cloud SQL and other Google services
resource "google_compute_global_address" "private_ip_range" {
  name          = "landright-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
  project       = var.project_id
}

# Service networking connection for private Cloud SQL
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]

  depends_on = [time_sleep.wait_for_apis]
}

# ------------------------------------------------------------------------------
# Note: VPC Access Connector removed for cost savings (~$15/month)
# Cloud Run uses Direct VPC Egress instead via network_interfaces
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# Cloud SQL PostgreSQL - db-f1-micro (cheapest tier)
# ------------------------------------------------------------------------------
resource "google_sql_database_instance" "postgres" {
  name                = var.db_instance_name
  region              = var.region
  database_version    = "POSTGRES_15"
  project             = var.project_id
  deletion_protection = false # Set to true for production

  settings {
    tier              = var.db_tier
    availability_type = "ZONAL" # Single zone for cost savings
    disk_type         = "PD_HDD" # Cheaper than SSD
    disk_size         = 10 # Minimum size
    disk_autoresize   = true

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.vpc.id
      enable_private_path_for_google_cloud_services = true
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = false # Disable for cost savings
      backup_retention_settings {
        retained_backups = 7
      }
    }

    maintenance_window {
      day  = 7 # Sunday
      hour = 3
    }

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }

    user_labels = local.common_labels
  }

  depends_on = [
    google_service_networking_connection.private_vpc_connection,
    time_sleep.wait_for_apis
  ]
}

resource "google_sql_database" "app" {
  name     = var.database_name
  instance = google_sql_database_instance.postgres.name
  project  = var.project_id
}

resource "google_sql_user" "app" {
  name     = var.db_user
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
  project  = var.project_id
}

# ------------------------------------------------------------------------------
# Memorystore Redis - Basic tier (cheapest, no HA)
# ------------------------------------------------------------------------------
resource "google_redis_instance" "cache" {
  name               = "landright-redis"
  tier               = "BASIC" # No HA, cheapest option
  memory_size_gb     = var.redis_memory_gb
  region             = var.region
  project            = var.project_id
  authorized_network = google_compute_network.vpc.id
  redis_version      = "REDIS_7_0"
  display_name       = "LandRight Redis Cache"

  labels = local.common_labels

  depends_on = [time_sleep.wait_for_apis]
}

# ------------------------------------------------------------------------------
# Artifact Registry - Container images
# ------------------------------------------------------------------------------
resource "google_artifact_registry_repository" "containers" {
  location      = var.artifact_repo_location
  repository_id = "landright"
  format        = "DOCKER"
  description   = "Container images for LandRight services"
  project       = var.project_id

  labels = local.common_labels

  depends_on = [time_sleep.wait_for_apis]
}

# ------------------------------------------------------------------------------
# Cloud Storage - Evidence and documents bucket
# ------------------------------------------------------------------------------
resource "google_storage_bucket" "evidence" {
  name                        = "${var.project_id}-evidence"
  location                    = var.region
  project                     = var.project_id
  force_destroy               = false
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 365
    }
  }

  labels = local.common_labels

  depends_on = [time_sleep.wait_for_apis]
}

# ------------------------------------------------------------------------------
# Pub/Sub - Async event processing
# ------------------------------------------------------------------------------
resource "google_pubsub_topic" "events" {
  name    = "landright-events"
  project = var.project_id

  message_retention_duration = "604800s" # 7 days

  labels = local.common_labels

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_pubsub_subscription" "events_push" {
  name    = "landright-events-push"
  topic   = google_pubsub_topic.events.id
  project = var.project_id

  ack_deadline_seconds = 60

  # Push to Cloud Run endpoint (configured after Cloud Run is deployed)
  # push_config {
  #   push_endpoint = "${google_cloud_run_v2_service.api.uri}/webhooks/pubsub"
  # }

  labels = local.common_labels
}
