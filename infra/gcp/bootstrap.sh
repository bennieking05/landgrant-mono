#!/bin/bash
# ------------------------------------------------------------------------------
# Bootstrap script for LandRight GCP infrastructure
# Run this ONCE before running terraform init/apply
# ------------------------------------------------------------------------------

set -e

# Configuration
PROJECT_ID="genuine-park-487014-a7"
BILLING_ACCOUNT="010525-01B070-3501CE"
REGION="us-central1"
STATE_BUCKET="${PROJECT_ID}-tfstate"

echo "=== LandRight GCP Bootstrap ==="
echo "Project: ${PROJECT_ID}"
echo "Billing Account: ${BILLING_ACCOUNT}"
echo "Region: ${REGION}"
echo ""

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1 > /dev/null 2>&1; then
    echo "Error: Not authenticated with gcloud. Run 'gcloud auth login' first."
    exit 1
fi

# Set project
echo "1. Setting project..."
gcloud config set project ${PROJECT_ID}

# Link billing account
echo "2. Linking billing account..."
gcloud billing projects link ${PROJECT_ID} --billing-account=${BILLING_ACCOUNT} || true

# Enable required APIs for bootstrap
echo "3. Enabling bootstrap APIs..."
gcloud services enable \
    cloudresourcemanager.googleapis.com \
    iam.googleapis.com \
    storage.googleapis.com \
    --project=${PROJECT_ID}

# Create Terraform state bucket
echo "4. Creating Terraform state bucket..."
if gsutil ls -b gs://${STATE_BUCKET} > /dev/null 2>&1; then
    echo "   Bucket already exists: gs://${STATE_BUCKET}"
else
    gsutil mb -p ${PROJECT_ID} -l ${REGION} -b on gs://${STATE_BUCKET}
    gsutil versioning set on gs://${STATE_BUCKET}
    echo "   Created bucket: gs://${STATE_BUCKET}"
fi

# Enable uniform bucket-level access
gsutil ubla set on gs://${STATE_BUCKET} 2>/dev/null || true

echo ""
echo "=== Bootstrap Complete ==="
echo ""
echo "Next steps:"
echo "1. cd infra/gcp"
echo "2. terraform init"
echo "3. terraform plan -var-file=environments/dev.tfvars"
echo "4. terraform apply -var-file=environments/dev.tfvars"
echo ""
echo "After Terraform apply, build and deploy the application:"
echo "5. cd ../../backend"
echo "6. gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/landright/api:latest"
echo "7. cd ../frontend && npm run build"
echo "8. gsutil -m rsync -r -d dist gs://${PROJECT_ID}-frontend"
