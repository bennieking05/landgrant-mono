# ------------------------------------------------------------------------------
# Secret Manager - Store all sensitive configuration
# ------------------------------------------------------------------------------

# Database password (auto-generated)
resource "random_password" "db_password" {
  length  = 32
  special = true
  override_special = "!#$%&*()-_=+[]{}:?"
}

resource "google_secret_manager_secret" "db_password" {
  secret_id = "landright-db-password"
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
  secret_id = "landright-jwt-secret"
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
  secret_id = "landright-app-config"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = local.common_labels

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_secret_manager_secret_version" "app_config" {
  secret      = google_secret_manager_secret.app_config.id
  secret_data = jsonencode({
    environment      = var.environment
    app_name         = "landright-api"
    jwt_audience     = "landright"
    jwt_issuer       = "https://auth.landright.app"
    gemini_model     = var.gemini_model
    gemini_location  = var.gemini_location
    enable_otlp      = true
    allowed_origins  = ["*"]
  })
}

# ------------------------------------------------------------------------------
# Gemini / Vertex AI API Key
# Note: For GCP-hosted services, we use IAM (service account) instead of API key.
# This secret is for external access or backup authentication.
# ------------------------------------------------------------------------------
resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "landright-gemini-api-key"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = local.common_labels

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_secret_manager_secret_version" "gemini_api_key" {
  secret      = google_secret_manager_secret.gemini_api_key.id
  secret_data = "USE_SERVICE_ACCOUNT_ADC"  # Placeholder - Cloud Run uses IAM
}

# ------------------------------------------------------------------------------
# SendGrid API Key (for email notifications)
# ------------------------------------------------------------------------------
resource "google_secret_manager_secret" "sendgrid_api_key" {
  secret_id = "landright-sendgrid-api-key"
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
    ignore_changes = [secret_data]  # Don't overwrite if manually updated
  }
}

# ------------------------------------------------------------------------------
# Twilio credentials (for SMS notifications)
# ------------------------------------------------------------------------------
resource "google_secret_manager_secret" "twilio_account_sid" {
  secret_id = "landright-twilio-account-sid"
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
  secret_id = "landright-twilio-auth-token"
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
  secret_id = "landright-twilio-from-number"
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
  secret_id = "landright-encryption-key"
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
  secret_id = "landright-session-secret"
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
  secret_id = "landright-docusign-integration-key"
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
  secret_id = "landright-docusign-secret-key"
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
    "landright-db-password",
    "landright-jwt-secret",
    "landright-app-config",
    "landright-gemini-api-key",
    "landright-sendgrid-api-key",
    "landright-twilio-account-sid",
    "landright-twilio-auth-token",
    "landright-twilio-from-number",
    "landright-encryption-key",
    "landright-session-secret",
    "landright-docusign-integration-key",
    "landright-docusign-secret-key",
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
