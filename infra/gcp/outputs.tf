# ------------------------------------------------------------------------------
# Terraform Outputs
# ------------------------------------------------------------------------------

# Cloud Run
output "api_url" {
  value       = google_cloud_run_v2_service.api.uri
  description = "URL of the LandRight API on Cloud Run"
}

output "worker_url" {
  value       = google_cloud_run_v2_service.worker.uri
  description = "URL of the LandRight worker on Cloud Run"
}

# Frontend
output "frontend_url" {
  value       = "https://${var.app_domain}"
  description = "URL of the frontend static site"
}

output "frontend_bucket" {
  value       = google_storage_bucket.frontend.name
  description = "GCS bucket name for frontend static files"
}

output "frontend_ip" {
  description = "Static IP for frontend - ADD THIS TO DNS"
  value       = google_compute_global_address.frontend_lb.address
}

# API Domain
output "api_custom_url" {
  value       = "https://${var.api_domain}"
  description = "Custom domain URL for the API"
}

output "api_domain_records" {
  description = "DNS records needed for API domain"
  value       = "Add CNAME record: api -> ghs.googlehosted.com"
}

# DNS Instructions
output "dns_instructions" {
  value = <<-EOT
    
    ========== DNS CONFIGURATION REQUIRED ==========
    
    Add these records in your domain registrar:
    
    1. Frontend (${var.app_domain}):
       Type: A
       Host: app
       Value: ${google_compute_global_address.frontend_lb.address}
       TTL: 300
    
    2. API (${var.api_domain}):
       Type: CNAME
       Host: api
       Value: ghs.googlehosted.com.
       TTL: 300
    
    After adding DNS records, wait 5-15 minutes for propagation,
    then run: terraform apply -var-file=environments/dev.tfvars
    
    SSL certificates will auto-provision once DNS is verified.
    ================================================
    
  EOT
}

# Database
output "cloud_sql_connection" {
  value       = google_sql_database_instance.postgres.connection_name
  description = "Cloud SQL connection name"
}

output "cloud_sql_private_ip" {
  value       = google_sql_database_instance.postgres.private_ip_address
  description = "Cloud SQL private IP address"
}

# Redis
output "redis_host" {
  value       = google_redis_instance.cache.host
  description = "Redis host IP"
}

output "redis_port" {
  value       = google_redis_instance.cache.port
  description = "Redis port"
}

# Storage
output "evidence_bucket" {
  value       = google_storage_bucket.evidence.name
  description = "GCS bucket for evidence and documents"
}

# Artifact Registry
output "artifact_registry_url" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.containers.repository_id}"
  description = "Artifact Registry repository URL for container images"
}

# Service Accounts
output "cloudrun_service_account" {
  value       = google_service_account.cloudrun.email
  description = "Service account used by Cloud Run"
}

output "cloudbuild_service_account" {
  value       = google_service_account.cloudbuild.email
  description = "Service account used by Cloud Build"
}

# Secrets (names only, not values)
output "secrets" {
  value = {
    # Auto-generated (ready to use)
    db_password     = google_secret_manager_secret.db_password.secret_id
    jwt_secret      = google_secret_manager_secret.jwt_secret.secret_id
    encryption_key  = google_secret_manager_secret.encryption_key.secret_id
    session_secret  = google_secret_manager_secret.session_secret.secret_id
    app_config      = google_secret_manager_secret.app_config.secret_id
    
    # Need to be populated with real keys
    gemini_api_key           = google_secret_manager_secret.gemini_api_key.secret_id
    sendgrid_api_key         = google_secret_manager_secret.sendgrid_api_key.secret_id
    twilio_account_sid       = google_secret_manager_secret.twilio_account_sid.secret_id
    twilio_auth_token        = google_secret_manager_secret.twilio_auth_token.secret_id
    twilio_from_number       = google_secret_manager_secret.twilio_from_number.secret_id
    docusign_integration_key = google_secret_manager_secret.docusign_integration_key.secret_id
    docusign_secret_key      = google_secret_manager_secret.docusign_secret_key.secret_id
  }
  description = "Secret Manager secret IDs"
}

output "secrets_to_populate" {
  value = <<-EOT
    After terraform apply, run the following to populate secrets with real API keys:
    
    chmod +x infra/gcp/scripts/populate-secrets.sh
    ./infra/gcp/scripts/populate-secrets.sh
    
    Or manually update individual secrets:
    
    # SendGrid (email)
    echo -n 'YOUR_SENDGRID_API_KEY' | gcloud secrets versions add landright-sendgrid-api-key --data-file=-
    
    # Twilio (SMS)
    echo -n 'YOUR_ACCOUNT_SID' | gcloud secrets versions add landright-twilio-account-sid --data-file=-
    echo -n 'YOUR_AUTH_TOKEN' | gcloud secrets versions add landright-twilio-auth-token --data-file=-
    echo -n '+15551234567' | gcloud secrets versions add landright-twilio-from-number --data-file=-
    
    # DocuSign (e-signatures)
    echo -n 'YOUR_INTEGRATION_KEY' | gcloud secrets versions add landright-docusign-integration-key --data-file=-
    echo -n 'YOUR_SECRET_KEY' | gcloud secrets versions add landright-docusign-secret-key --data-file=-
  EOT
  description = "Instructions to populate secrets after deployment"
}

# Pub/Sub
output "pubsub_topic" {
  value       = google_pubsub_topic.events.name
  description = "Pub/Sub topic for async events"
}

# Deployment commands
output "deployment_commands" {
  value = <<-EOT
    # Build and push API container (from project root)
    docker build -t ${var.region}-docker.pkg.dev/${var.project_id}/landright/api:latest -f backend/Dockerfile .
    docker push ${var.region}-docker.pkg.dev/${var.project_id}/landright/api:latest

    # Build and push Worker container (from project root)
    docker build -t ${var.region}-docker.pkg.dev/${var.project_id}/landright/worker:latest -f backend/Dockerfile.worker .
    docker push ${var.region}-docker.pkg.dev/${var.project_id}/landright/worker:latest

    # Build and deploy frontend
    cd frontend && VITE_API_BASE=${google_cloud_run_v2_service.api.uri} npm run build
    gsutil -m rsync -r -d ./frontend/dist gs://${google_storage_bucket.frontend.name}

    # Update Cloud Run to use new image
    gcloud run services update landright-api --region ${var.region} --image ${var.region}-docker.pkg.dev/${var.project_id}/landright/api:latest
  EOT
  description = "Commands to deploy application updates"
}
