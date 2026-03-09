# ------------------------------------------------------------------------------
# Cloud Run - Backend API Service
# ------------------------------------------------------------------------------

resource "google_cloud_run_v2_service" "api" {
  name     = "landright-api"
  location = var.region
  project  = var.project_id

  template {
    service_account = google_service_account.cloudrun.email

    scaling {
      min_instance_count = var.cloudrun_min_instances
      max_instance_count = var.cloudrun_max_instances
    }

    # Direct VPC Egress (no VPC Access Connector needed - saves ~$15/mo)
    vpc_access {
      network_interfaces {
        network    = google_compute_network.vpc.id
        subnetwork = google_compute_subnetwork.workloads.id
      }
      egress = "PRIVATE_RANGES_ONLY"
    }

    containers {
      name  = "api"
      image = "${var.region}-docker.pkg.dev/${var.project_id}/landright/api:latest"

      resources {
        limits = {
          cpu    = var.cloudrun_cpu
          memory = var.cloudrun_memory
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      ports {
        container_port = 8080
      }

      # =======================================================================
      # Plain Environment Variables
      # =======================================================================
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "APP_NAME"
        value = "landright-api"
      }

      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }

      env {
        name  = "GEMINI_MODEL"
        value = var.gemini_model
      }

      env {
        name  = "GEMINI_LOCATION"
        value = var.gemini_location
      }

      env {
        name  = "GEMINI_ENABLED"
        value = "true"
      }

      env {
        name  = "EVIDENCE_BUCKET"
        value = google_storage_bucket.evidence.name
      }

      env {
        name  = "DATABASE_HOST"
        value = google_sql_database_instance.postgres.private_ip_address
      }

      env {
        name  = "DATABASE_NAME"
        value = var.database_name
      }

      env {
        name  = "DATABASE_USER"
        value = var.db_user
      }

      env {
        name  = "REDIS_HOST"
        value = google_redis_instance.cache.host
      }

      env {
        name  = "REDIS_PORT"
        value = tostring(google_redis_instance.cache.port)
      }

      env {
        name  = "NOTIFICATIONS_MODE"
        value = "send"
      }

      # =======================================================================
      # Secrets from Secret Manager
      # =======================================================================
      
      # Database password
      env {
        name = "DATABASE_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }

      # JWT secret
      env {
        name = "JWT_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.jwt_secret.secret_id
            version = "latest"
          }
        }
      }

      # Session secret
      env {
        name = "SESSION_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.session_secret.secret_id
            version = "latest"
          }
        }
      }

      # Encryption key
      env {
        name = "ENCRYPTION_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.encryption_key.secret_id
            version = "latest"
          }
        }
      }

      # SendGrid API key (email)
      env {
        name = "SENDGRID_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.sendgrid_api_key.secret_id
            version = "latest"
          }
        }
      }

      # Twilio (SMS)
      env {
        name = "TWILIO_ACCOUNT_SID"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.twilio_account_sid.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "TWILIO_AUTH_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.twilio_auth_token.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "TWILIO_FROM_NUMBER"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.twilio_from_number.secret_id
            version = "latest"
          }
        }
      }

      # DocuSign (e-signatures)
      env {
        name = "DOCUSIGN_INTEGRATION_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.docusign_integration_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "DOCUSIGN_SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.docusign_secret_key.secret_id
            version = "latest"
          }
        }
      }

      # =======================================================================
      # Health Probes
      # =======================================================================
      startup_probe {
        http_get {
          path = "/health/live"
          port = 8080
        }
        initial_delay_seconds = 5
        timeout_seconds       = 3
        period_seconds        = 5
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/health/live"
          port = 8080
        }
        timeout_seconds   = 3
        period_seconds    = 30
        failure_threshold = 3
      }
    }

    timeout = "300s"

    labels = local.common_labels
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  labels = local.common_labels

  depends_on = [
    google_secret_manager_secret_iam_member.cloudrun_access,
    google_artifact_registry_repository.containers,
    time_sleep.wait_for_apis
  ]

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
    ]
  }
}

# Note: Public access disabled due to org policy (iam.allowedPolicyMemberDomains)
# For dev, use authenticated access via gcloud or service account
# To enable public access, remove the org policy constraint
#
# resource "google_cloud_run_v2_service_iam_member" "public" {
#   project  = var.project_id
#   location = var.region
#   name     = google_cloud_run_v2_service.api.name
#   role     = "roles/run.invoker"
#   member   = "allUsers"
# }

# ------------------------------------------------------------------------------
# Domain Mapping for API (api.landrightiq.com)
# ------------------------------------------------------------------------------
resource "google_cloud_run_domain_mapping" "api" {
  name     = var.api_domain
  location = var.region
  project  = var.project_id

  metadata {
    namespace = var.project_id
  }

  spec {
    route_name = google_cloud_run_v2_service.api.name
  }

  depends_on = [google_cloud_run_v2_service.api]
}

# ------------------------------------------------------------------------------
# Cloud Run - Celery Worker (for background tasks)
# ------------------------------------------------------------------------------
resource "google_cloud_run_v2_service" "worker" {
  name     = "landright-worker"
  location = var.region
  project  = var.project_id

  template {
    service_account = google_service_account.cloudrun.email

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    # Direct VPC Egress (no VPC Access Connector needed - saves ~$15/mo)
    vpc_access {
      network_interfaces {
        network    = google_compute_network.vpc.id
        subnetwork = google_compute_subnetwork.workloads.id
      }
      egress = "PRIVATE_RANGES_ONLY"
    }

    containers {
      name  = "worker"
      image = "${var.region}-docker.pkg.dev/${var.project_id}/landright/worker:latest"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 5
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 3
      }

      # Plain environment variables
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }

      env {
        name  = "GEMINI_MODEL"
        value = var.gemini_model
      }

      env {
        name  = "GEMINI_LOCATION"
        value = var.gemini_location
      }

      env {
        name  = "EVIDENCE_BUCKET"
        value = google_storage_bucket.evidence.name
      }

      env {
        name  = "DATABASE_HOST"
        value = google_sql_database_instance.postgres.private_ip_address
      }

      env {
        name  = "DATABASE_NAME"
        value = var.database_name
      }

      env {
        name  = "DATABASE_USER"
        value = var.db_user
      }

      env {
        name  = "REDIS_HOST"
        value = google_redis_instance.cache.host
      }

      env {
        name  = "REDIS_PORT"
        value = tostring(google_redis_instance.cache.port)
      }

      # Secrets
      env {
        name = "DATABASE_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "JWT_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.jwt_secret.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "SENDGRID_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.sendgrid_api_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "TWILIO_ACCOUNT_SID"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.twilio_account_sid.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "TWILIO_AUTH_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.twilio_auth_token.secret_id
            version = "latest"
          }
        }
      }
    }

    timeout = "900s"

    labels = local.common_labels
  }

  labels = local.common_labels

  depends_on = [
    google_secret_manager_secret_iam_member.cloudrun_access,
    google_artifact_registry_repository.containers,
    time_sleep.wait_for_apis
  ]

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
    ]
  }
}
