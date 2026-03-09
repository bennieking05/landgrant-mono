# LandRight GCP Infrastructure

Terraform configuration for deploying LandRight to Google Cloud Platform.

## Architecture

- **Compute**: Cloud Run (serverless, pay-per-request)
- **Database**: Cloud SQL PostgreSQL (db-f1-micro for testing)
- **Cache**: Memorystore Redis (Basic tier, 1GB)
- **AI**: Vertex AI Gemini 1.5 Flash
- **Frontend**: Cloud Storage + Cloud CDN
- **Secrets**: Secret Manager

## Prerequisites

1. Google Cloud SDK (`gcloud`) installed and authenticated
2. Terraform >= 1.6.0
3. Billing account access: `012FC5-228A56-495D5E`
4. Project: `landright-483916`

## Quick Start

### 1. Authenticate with GCP

```bash
gcloud auth login
gcloud auth application-default login
```

### 2. Run Bootstrap Script

```bash
cd infra/gcp
chmod +x bootstrap.sh
./bootstrap.sh
```

This creates the Terraform state bucket and enables required APIs.

### 3. Initialize Terraform

```bash
terraform init
```

### 4. Review the Plan

```bash
terraform plan -var-file=environments/dev.tfvars
```

### 5. Apply Infrastructure

```bash
terraform apply -var-file=environments/dev.tfvars
```

### 6. Build and Deploy Application

```bash
# Backend API
cd ../../backend
gcloud builds submit --tag us-central1-docker.pkg.dev/landright-483916/landright/api:latest

# Frontend
cd ../frontend
npm run build
gsutil -m rsync -r -d dist gs://landright-483916-frontend
```

## File Structure

```
infra/gcp/
├── providers.tf      # Terraform providers and backend config
├── variables.tf      # Input variables
├── billing.tf        # Billing linkage and API enablement
├── main.tf           # VPC, Cloud SQL, Redis, Storage
├── iam.tf            # Service accounts and IAM bindings
├── secrets.tf        # Secret Manager secrets
├── cloudrun.tf       # Cloud Run services (API + Worker)
├── frontend.tf       # Static hosting with CDN
├── outputs.tf        # Output values
├── bootstrap.sh      # One-time setup script
└── environments/
    └── dev.tfvars    # Dev environment variables
```

## Cost Estimate (Testing Tier)

| Resource | Monthly Est. |
|----------|--------------|
| Cloud SQL db-f1-micro | ~$9 |
| Redis Basic 1GB | ~$35 |
| Cloud Run (low traffic) | ~$0-5 |
| Cloud Storage | ~$1 |
| Vertex AI Gemini | Pay per token |
| **Total** | **~$50/month** |

## Secrets

After deployment, update these placeholder secrets in Secret Manager:

1. `landright-sendgrid-api-key` - SendGrid API key for email
2. `landright-twilio-credentials` - Twilio credentials for SMS

## Scaling to Production

To scale for production, update `environments/dev.tfvars`:

```hcl
# Cloud SQL
db_tier = "db-custom-2-7680"  # 2 vCPU, 7.5GB RAM

# Redis
redis_memory_gb = 4

# Cloud Run
cloudrun_min_instances = 1
cloudrun_max_instances = 10

# Gemini
gemini_model = "gemini-1.5-pro-001"
```

## Troubleshooting

### API Not Enabled Error
Wait 60 seconds after terraform apply starts - APIs need time to enable.

### Cloud SQL Connection Issues
Ensure VPC Access Connector is deployed and Cloud Run is configured to use it.

### Gemini API Errors
Verify the service account has `roles/aiplatform.user` permission.

## Useful Commands

```bash
# View Cloud Run logs
gcloud run services logs read landright-api --region us-central1

# View Cloud SQL connection info
gcloud sql instances describe landright-sql-dev

# Access Secret Manager
gcloud secrets versions access latest --secret=landright-db-password

# Invalidate CDN cache
gcloud compute url-maps invalidate-cdn-cache landright-frontend-urlmap --path="/*"
```
