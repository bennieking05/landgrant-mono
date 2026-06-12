# ------------------------------------------------------------------------------
# LandGrant — staging (LandGrantIQ)
#
# `project_id` is the Google Cloud **project ID** (Console → IAM → Settings).
# It is unrelated to the product name. Point it at the GCP project that should
# own staging Cloud Run, Cloud SQL, Redis, and the frontend bucket/LB.
# ------------------------------------------------------------------------------

# Project & billing
project_id        = "clearpath-490715"
billing_account   = "010525-01B070-3501CE"
environment       = "staging"
region            = "us-central1"

# Networking — /24 for Cloud Run direct VPC egress (must not overlap dev/prod)
subnet_cidr = "10.10.20.0/24"

# Cloud SQL
db_instance_name = "landgrant-sql-staging"
db_tier          = "db-custom-1-3840"
database_name    = "landgrant"
db_user          = "landgrant"

# Memorystore
redis_memory_gb = 1

# Cloud Run
cloudrun_min_instances = 0
cloudrun_max_instances = 4
cloudrun_memory        = "1Gi"
cloudrun_cpu           = "1"

# Vertex AI
gemini_model    = "gemini-1.5-flash-001"
gemini_location = "us-central1"

# Artifact Registry
artifact_repo_location = "us-central1"

# Frontend / DNS (Terraform + load balancer + Cloud CDN)
frontend_domain = ""

# Staging hostnames (DNS + managed certs)
app_domain  = "app-staging.landgrantiq.com"
api_domain  = "api-staging.landgrantiq.com"
apex_domain = "staging.landgrantiq.com"
# redirect_apex_to_app = true   # default: apex → app SPA
# redirect_www_to_apex = true   # default: www.<apex> → apex (marketing on Cloud Run)
