# ------------------------------------------------------------------------------
# Development Environment Configuration
# Uses lowest-cost tiers for testing
# ------------------------------------------------------------------------------

# Project & Billing
project_id      = "genuine-park-487014-a7"
billing_account = "010525-01B070-3501CE"
environment     = "dev"
region          = "us-central1"

# Networking - /24 required for Cloud Run Direct VPC Egress
subnet_cidr = "10.10.10.0/24"

# Cloud SQL - Cheapest tier
db_instance_name = "landright-sql-dev"
db_tier          = "db-f1-micro"
database_name    = "landright"
db_user          = "landright"

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

# Custom Domains for LandRightIQ.com
app_domain = "app.landrightiq.com"
api_domain = "api.landrightiq.com"
