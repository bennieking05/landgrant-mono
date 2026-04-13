variable "project_id" {
  type        = string
  description = "GCP project that hosts LandGrant."
  default     = "clearpath-490715"
}

variable "billing_account" {
  type        = string
  description = "Billing account ID to link to the project."
  default     = "010525-01B070-3501CE"
}

variable "region" {
  type        = string
  description = "Primary region for resources."
  default     = "us-central1"
}

variable "environment" {
  type        = string
  description = "Deployment environment label (dev/stage/prod)."
  default     = "dev"
}

# ------------------------------------------------------------------------------
# Networking
# ------------------------------------------------------------------------------
variable "subnet_cidr" {
  type        = string
  description = "CIDR for the private workload subnet."
  default     = "10.10.10.0/28"
}

# ------------------------------------------------------------------------------
# Cloud SQL (lowest tier for testing)
# ------------------------------------------------------------------------------
variable "db_instance_name" {
  type        = string
  description = "Cloud SQL instance name."
  default     = "landright-sql"
}

variable "db_tier" {
  type        = string
  description = "Cloud SQL machine tier. db-f1-micro is cheapest."
  default     = "db-f1-micro"
}

variable "database_name" {
  type        = string
  description = "Logical Postgres database name used by the app."
  default     = "landright"
}

variable "db_user" {
  type        = string
  description = "Database user for the application."
  default     = "landright"
}

# ------------------------------------------------------------------------------
# Redis (lowest tier for testing)
# ------------------------------------------------------------------------------
variable "redis_memory_gb" {
  type        = number
  description = "Redis memory size in GB. 1 is minimum."
  default     = 1
}

# ------------------------------------------------------------------------------
# Cloud Run
# ------------------------------------------------------------------------------
variable "cloudrun_min_instances" {
  type        = number
  description = "Minimum Cloud Run instances. 0 allows scale-to-zero."
  default     = 0
}

variable "cloudrun_max_instances" {
  type        = number
  description = "Maximum Cloud Run instances."
  default     = 2
}

variable "cloudrun_memory" {
  type        = string
  description = "Memory allocation for Cloud Run."
  default     = "512Mi"
}

variable "cloudrun_cpu" {
  type        = string
  description = "CPU allocation for Cloud Run."
  default     = "1"
}

# ------------------------------------------------------------------------------
# Vertex AI / Gemini
# ------------------------------------------------------------------------------
variable "gemini_model" {
  type        = string
  description = "Gemini model to use. Flash is cheaper than Pro."
  default     = "gemini-1.5-flash-001"
}

variable "gemini_location" {
  type        = string
  description = "Location for Vertex AI."
  default     = "us-central1"
}

# ------------------------------------------------------------------------------
# Frontend
# ------------------------------------------------------------------------------
variable "frontend_domain" {
  type        = string
  description = "Custom domain for frontend (optional, leave empty for bucket URL)."
  default     = ""
}

# ------------------------------------------------------------------------------
# Custom Domains
# ------------------------------------------------------------------------------
variable "app_domain" {
  description = "Domain for the frontend application"
  type        = string
  default     = "app.landgrantiq.com"
}

variable "api_domain" {
  description = "Domain for the API"
  type        = string
  default     = "api.landgrantiq.com"
}

variable "apex_domain" {
  description = "Optional apex hostname (e.g. landgrantiq.com). When set, marketing is mapped via Cloud Run domain mapping with Google-managed TLS; DNS uses Cloud Run anycast A records (see terraform output dns_instructions), not the frontend load balancer IP."
  type        = string
  default     = ""
}

variable "redirect_apex_to_app" {
  description = "If true and apex_domain is set, HTTP(S) requests to the apex host 301-redirect to app_domain (recommended). If false, apex serves the same SPA as app (not recommended for production)."
  type        = bool
  default     = true
}

variable "redirect_www_to_apex" {
  description = "If true and apex_domain is set, www.<apex> 301-redirects to the apex host (@), e.g. www.landgrantiq.com -> landgrantiq.com."
  type        = bool
  default     = true
}

# ------------------------------------------------------------------------------
# Artifact Registry
# ------------------------------------------------------------------------------
variable "artifact_repo_location" {
  type        = string
  description = "Region for Artifact Registry repo."
  default     = "us-central1"
}
