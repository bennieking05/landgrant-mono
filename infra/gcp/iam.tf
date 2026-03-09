# ------------------------------------------------------------------------------
# Service Accounts
# ------------------------------------------------------------------------------

# Cloud Run service account - runs the backend API
resource "google_service_account" "cloudrun" {
  account_id   = "landright-cloudrun"
  display_name = "LandRight Cloud Run Service Account"
  description  = "Service account for LandRight backend API on Cloud Run"
  project      = var.project_id

  depends_on = [time_sleep.wait_for_apis]
}

# Cloud Build service account - builds and deploys containers
resource "google_service_account" "cloudbuild" {
  account_id   = "landright-cloudbuild"
  display_name = "LandRight Cloud Build Service Account"
  description  = "Service account for building and deploying LandRight"
  project      = var.project_id

  depends_on = [time_sleep.wait_for_apis]
}

# ------------------------------------------------------------------------------
# IAM Bindings for Cloud Run Service Account
# ------------------------------------------------------------------------------

# Access Cloud SQL
resource "google_project_iam_member" "cloudrun_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloudrun.email}"
}

# Access Cloud Storage (evidence bucket)
resource "google_project_iam_member" "cloudrun_storage_object_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.cloudrun.email}"
}

# Access Vertex AI (Gemini)
resource "google_project_iam_member" "cloudrun_aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.cloudrun.email}"
}

# Write logs
resource "google_project_iam_member" "cloudrun_logging_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloudrun.email}"
}

# Write traces
resource "google_project_iam_member" "cloudrun_trace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.cloudrun.email}"
}

# Write metrics
resource "google_project_iam_member" "cloudrun_monitoring_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.cloudrun.email}"
}

# Pub/Sub publisher (for async events)
resource "google_project_iam_member" "cloudrun_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.cloudrun.email}"
}

# ------------------------------------------------------------------------------
# IAM Bindings for Cloud Build Service Account
# ------------------------------------------------------------------------------

# Deploy to Cloud Run
resource "google_project_iam_member" "cloudbuild_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# Push to Artifact Registry
resource "google_project_iam_member" "cloudbuild_artifact_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# Act as Cloud Run service account
resource "google_service_account_iam_member" "cloudbuild_act_as_cloudrun" {
  service_account_id = google_service_account.cloudrun.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# Write logs
resource "google_project_iam_member" "cloudbuild_logging_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# Read secrets (for build-time secrets if needed)
resource "google_project_iam_member" "cloudbuild_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}

# Upload to Cloud Storage (for frontend)
resource "google_project_iam_member" "cloudbuild_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}
