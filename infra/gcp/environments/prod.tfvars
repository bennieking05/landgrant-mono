# ------------------------------------------------------------------------------
# Production — tighten deletion_protection, min instances, and DB tier before
# apply. Use a production billing project and rotate all secrets via Secret Manager.
# ------------------------------------------------------------------------------

project_id      = "clearpath-490715"
billing_account = "010525-01B070-3501CE"
environment     = "prod"
region          = "us-central1"

subnet_cidr = "10.10.30.0/24"

db_instance_name = "landgrant-sql-prod"
db_tier          = "db-custom-2-7680"
database_name    = "landgrant"
db_user          = "landgrant"

redis_memory_gb = 2

cloudrun_min_instances = 1
cloudrun_max_instances = 10
cloudrun_memory        = "2Gi"
cloudrun_cpu           = "2"

gemini_model    = "gemini-1.5-flash-001"
gemini_location = "us-central1"

artifact_repo_location = "us-central1"

frontend_domain = ""

app_domain  = "app.landgrantiq.com"
api_domain  = "api.landgrantiq.com"
apex_domain = "landgrantiq.com"
