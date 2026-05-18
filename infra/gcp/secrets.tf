# ------------------------------------------------------------------------------
# Secret Manager - Store all sensitive configuration
# ------------------------------------------------------------------------------

# Database password (auto-generated)
resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}:?"
}

resource "google_secret_manager_secret" "db_password" {
  secret_id = "landgrant-db-password"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = local.common_labels

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

# JWT Secret for authentication (auto-generated)
resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "landgrant-jwt-secret"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = local.common_labels

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_secret_manager_secret_version" "jwt_secret" {
  secret      = google_secret_manager_secret.jwt_secret.id
  secret_data = random_password.jwt_secret.result
}

# Application configuration secret (JSON blob)
resource "google_secret_manager_secret" "app_config" {
  secret_id = "landgrant-app-config"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = local.common_labels

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_secret_manager_secret_version" "app_config" {
  secret = google_secret_manager_secret.app_config.id
  secret_data = jsonencode({
    environment     = var.environment
    app_name        = "landgrant-api"
    jwt_audience    = "landgrant"
    jwt_issuer      = "https://auth.landgrant.local"
    gemini_model    = var.gemini_model
    gemini_location = var.gemini_location
    enable_otlp     = true
    # CORS allowlist is derived from the known frontend domains. We explicitly
    # refuse to ship a wildcard here — the API enforces
    # ``validate_prod_secrets`` on startup and a ["*"] value would fail that
    # guard. ``app_domain`` is the primary SPA host; ``apex_domain`` covers
    # the marketing redirect target when configured.
    allowed_origins = compact([
      "https://${var.app_domain}",
      var.apex_domain != "" ? "https://${var.apex_domain}" : "",
      var.apex_domain != "" ? "https://www.${var.apex_domain}" : "",
    ])
  })
}

# ------------------------------------------------------------------------------
# Gemini / Vertex AI API Key
# Note: For GCP-hosted services, we use IAM (service account) instead of API key.
# This secret is for external access or backup authentication.
# ------------------------------------------------------------------------------
resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "landgrant-gemini-api-key"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = local.common_labels

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_secret_manager_secret_version" "gemini_api_key" {
  secret      = google_secret_manager_secret.gemini_api_key.id
  secret_data = "USE_SERVICE_ACCOUNT_ADC" # Placeholder - Cloud Run uses IAM
}

# ------------------------------------------------------------------------------
# SendGrid API Key (for email notifications)
# ------------------------------------------------------------------------------
resource "google_secret_manager_secret" "sendgrid_api_key" {
  secret_id = "landgrant-sendgrid-api-key"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = local.common_labels

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_secret_manager_secret_version" "sendgrid_api_key" {
  secret      = google_secret_manager_secret.sendgrid_api_key.id
  secret_data = "PLACEHOLDER_UPDATE_WITH_REAL_KEY"

  lifecycle {
    ignore_changes = [secret_data] # Don't overwrite if manually updated
  }
}

# ------------------------------------------------------------------------------
# Twilio credentials (for SMS notifications)
# ------------------------------------------------------------------------------
resource "google_secret_manager_secret" "twilio_account_sid" {
  secret_id = "landgrant-twilio-account-sid"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = local.common_labels

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_secret_manager_secret_version" "twilio_account_sid" {
  secret      = google_secret_manager_secret.twilio_account_sid.id
  secret_data = "PLACEHOLDER_UPDATE_WITH_REAL_SID"

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret" "twilio_auth_token" {
  secret_id = "landgrant-twilio-auth-token"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = local.common_labels

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_secret_manager_secret_version" "twilio_auth_token" {
  secret      = google_secret_manager_secret.twilio_auth_token.id
  secret_data = "PLACEHOLDER_UPDATE_WITH_REAL_TOKEN"

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret" "twilio_from_number" {
  secret_id = "landgrant-twilio-from-number"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = local.common_labels

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_secret_manager_secret_version" "twilio_from_number" {
  secret      = google_secret_manager_secret.twilio_from_number.id
  secret_data = "+1XXXXXXXXXX"

  lifecycle {
    ignore_changes = [secret_data]
  }
}

# ------------------------------------------------------------------------------
# Encryption key for client-side encryption (auto-generated)
# ------------------------------------------------------------------------------
resource "random_password" "encryption_key" {
  length  = 32
  special = false
}

resource "google_secret_manager_secret" "encryption_key" {
  secret_id = "landgrant-encryption-key"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = local.common_labels

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_secret_manager_secret_version" "encryption_key" {
  secret      = google_secret_manager_secret.encryption_key.id
  secret_data = random_password.encryption_key.result
}

# ------------------------------------------------------------------------------
# Session secret for web sessions (auto-generated)
# ------------------------------------------------------------------------------
resource "random_password" "session_secret" {
  length  = 48
  special = false
}

resource "google_secret_manager_secret" "session_secret" {
  secret_id = "landgrant-session-secret"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = local.common_labels

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_secret_manager_secret_version" "session_secret" {
  secret      = google_secret_manager_secret.session_secret.id
  secret_data = random_password.session_secret.result
}

# ------------------------------------------------------------------------------
# DocuSign integration (for e-signatures)
# ------------------------------------------------------------------------------
resource "google_secret_manager_secret" "docusign_integration_key" {
  secret_id = "landgrant-docusign-integration-key"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = local.common_labels

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_secret_manager_secret_version" "docusign_integration_key" {
  secret      = google_secret_manager_secret.docusign_integration_key.id
  secret_data = "PLACEHOLDER_UPDATE_WITH_REAL_KEY"

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret" "docusign_secret_key" {
  secret_id = "landgrant-docusign-secret-key"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = local.common_labels

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_secret_manager_secret_version" "docusign_secret_key" {
  secret      = google_secret_manager_secret.docusign_secret_key.id
  secret_data = "PLACEHOLDER_UPDATE_WITH_REAL_KEY"

  lifecycle {
    ignore_changes = [secret_data]
  }
}

# ------------------------------------------------------------------------------
# IAM - Allow Cloud Run service account to access ALL secrets
# Use static secret names to avoid for_each dependency issues
# ------------------------------------------------------------------------------
locals {
  cloudrun_secret_ids = [
    "landgrant-db-password",
    "landgrant-jwt-secret",
    "landgrant-app-config",
    "landgrant-gemini-api-key",
    "landgrant-sendgrid-api-key",
    "landgrant-twilio-account-sid",
    "landgrant-twilio-auth-token",
    "landgrant-twilio-from-number",
    "landgrant-encryption-key",
    "landgrant-session-secret",
    "landgrant-docusign-integration-key",
    "landgrant-docusign-secret-key",
  ]
}

resource "google_secret_manager_secret_iam_member" "cloudrun_access" {
  for_each  = toset(local.cloudrun_secret_ids)
  secret_id = each.value
  project   = var.project_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloudrun.email}"

  depends_on = [
    google_secret_manager_secret.db_password,
    google_secret_manager_secret.jwt_secret,
    google_secret_manager_secret.app_config,
    google_secret_manager_secret.gemini_api_key,
    google_secret_manager_secret.sendgrid_api_key,
    google_secret_manager_secret.twilio_account_sid,
    google_secret_manager_secret.twilio_auth_token,
    google_secret_manager_secret.twilio_from_number,
    google_secret_manager_secret.encryption_key,
    google_secret_manager_secret.session_secret,
    google_secret_manager_secret.docusign_integration_key,
    google_secret_manager_secret.docusign_secret_key,
    google_service_account.cloudrun,
  ]
}
