# ------------------------------------------------------------------------------
# Billing Account Linkage
# ------------------------------------------------------------------------------
# Note: This requires the user running Terraform to have billing.accounts.getIamPolicy
# and billing.accounts.setIamPolicy permissions on the billing account.

resource "google_billing_project_info" "default" {
  project         = var.project_id
  billing_account = var.billing_account
}

# ------------------------------------------------------------------------------
# Enable Required GCP APIs
# ------------------------------------------------------------------------------
resource "google_project_service" "required" {
  for_each = toset([
    # Core Infrastructure
    "compute.googleapis.com",
    "vpcaccess.googleapis.com",
    "servicenetworking.googleapis.com",
    
    # Container & Build
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "containerregistry.googleapis.com",
    
    # Database & Cache
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    
    # AI / ML
    "aiplatform.googleapis.com",
    
    # Security & Secrets
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    
    # Storage
    "storage.googleapis.com",
    "storage-component.googleapis.com",
    
    # Monitoring & Logging
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudtrace.googleapis.com",
    
    # Pub/Sub (for async workflows)
    "pubsub.googleapis.com",
  ])

  project                    = var.project_id
  service                    = each.value
  disable_on_destroy         = false
  disable_dependent_services = false

  depends_on = [google_billing_project_info.default]
}

# Wait for APIs to be fully enabled before creating resources
resource "time_sleep" "wait_for_apis" {
  depends_on      = [google_project_service.required]
  create_duration = "60s"
}
