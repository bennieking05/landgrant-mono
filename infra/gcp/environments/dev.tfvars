# ------------------------------------------------------------------------------
# Development Environment Configuration
# Uses lowest-cost tiers for testing
# ------------------------------------------------------------------------------

# Project & Billing
project_id      = "clearpath-490715"
billing_account = "010525-01B070-3501CE"
environment     = "dev"
region          = "us-central1"

# Networking - /24 required for Cloud Run Direct VPC Egress
subnet_cidr = "10.10.10.0/24"

# Cloud SQL - Cheapest tier (instance name must match existing Terraform/GCP state)
db_instance_name = "landgrant-sql-dev"
db_tier          = "db-f1-micro"
database_name    = "landgrant"
db_user          = "landgrant"

# Redis - Minimum size
redis_memory_gb = 1

# Cloud Run - Scale to zero
cloudrun_min_instances = 0
cloudrun_max_instances = 2
cloudrun_memory        = "512Mi"
cloudrun_cpu           = "1"

# Vertex AI / Gemini - Use Flash (cheaper than Pro)
gemini_model    = "gemini-1.5-flash-001"
gemini_location = "us-central1"

# Artifact Registry
artifact_repo_location = "us-central1"

# Frontend (no custom domain for dev)
frontend_domain = ""

# Custom Domains for LandGrantIQ.com
# Canonical frontend URL: https://app.landgrantiq.com (apex redirects here when redirect_apex_to_app = true)
app_domain  = "app.landgrantiq.com"
api_domain  = "api.landgrantiq.com"
apex_domain = "landgrantiq.com"
# redirect_apex_to_app = true  # default; set false only if you must serve the SPA on both hostnames
