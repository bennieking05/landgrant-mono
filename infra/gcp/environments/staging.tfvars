# ------------------------------------------------------------------------------
# Staging — isolated DB/Redis from dev/prod (apply to a dedicated GCP project or
# distinct instance names). Adjust project_id and instance names before apply.
# ------------------------------------------------------------------------------

project_id      = "clearpath-490715"
billing_account = "010525-01B070-3501CE"
environment     = "staging"
region          = "us-central1"

subnet_cidr = "10.10.20.0/24"

db_instance_name = "landgrant-sql-staging"
db_tier          = "db-custom-1-3840"
database_name    = "landgrant"
db_user          = "landgrant"

redis_memory_gb = 1

cloudrun_min_instances = 0
cloudrun_max_instances = 4
cloudrun_memory        = "1Gi"
cloudrun_cpu           = "1"

gemini_model    = "gemini-1.5-flash-001"
gemini_location = "us-central1"

artifact_repo_location = "us-central1"

frontend_domain = ""

app_domain  = "app-staging.landgrantiq.com"
api_domain  = "api-staging.landgrantiq.com"
apex_domain = "staging.landgrantiq.com"
