variable "project_id" {
  type        = string
  description = "GCP project that hosts LandRight."
  default     = "landright-483916"
}

variable "billing_account" {
  type        = string
  description = "Billing account ID to link to the project."
  default     = "012FC5-228A56-495D5E"
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
  default     = "app.landrightiq.com"
}

variable "api_domain" {
  description = "Domain for the API"
  type        = string
  default     = "api.landrightiq.com"
}

# ------------------------------------------------------------------------------
# Artifact Registry
# ------------------------------------------------------------------------------
variable "artifact_repo_location" {
  type        = string
  description = "Region for Artifact Registry repo."
  default     = "us-central1"
}
