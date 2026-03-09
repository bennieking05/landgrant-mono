#!/bin/bash
# ------------------------------------------------------------------------------
# Populate Secret Manager with real API keys
# Run this after terraform apply to update placeholder secrets
# ------------------------------------------------------------------------------

set -e

PROJECT_ID="landright-483916"

echo "=== LandRight Secret Manager Setup ==="
echo "Project: ${PROJECT_ID}"
echo ""
echo "This script will help you populate secrets in Secret Manager."
echo "Press Ctrl+C to cancel at any time."
echo ""

# Function to update a secret
update_secret() {
    local secret_id=$1
    local prompt=$2
    local current_value
    
    current_value=$(gcloud secrets versions access latest --secret="${secret_id}" --project="${PROJECT_ID}" 2>/dev/null || echo "")
    
    if [[ "$current_value" == "PLACEHOLDER"* ]] || [[ "$current_value" == "USE_SERVICE"* ]] || [[ "$current_value" == "+1XXXX"* ]]; then
        echo ""
        echo "Secret: ${secret_id}"
        echo "Current: (placeholder)"
        read -p "${prompt}: " new_value
        
        if [ -n "$new_value" ]; then
            echo -n "$new_value" | gcloud secrets versions add "${secret_id}" \
                --data-file=- \
                --project="${PROJECT_ID}"
            echo "✓ Updated ${secret_id}"
        else
            echo "⏭ Skipped ${secret_id}"
        fi
    else
        echo "✓ ${secret_id} already configured"
    fi
}

# Check authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1 > /dev/null 2>&1; then
    echo "Error: Not authenticated with gcloud. Run 'gcloud auth login' first."
    exit 1
fi

gcloud config set project ${PROJECT_ID}

echo ""
echo "=== SendGrid (Email) ==="
update_secret "landright-sendgrid-api-key" "Enter SendGrid API Key (or press Enter to skip)"

echo ""
echo "=== Twilio (SMS) ==="
update_secret "landright-twilio-account-sid" "Enter Twilio Account SID (or press Enter to skip)"
update_secret "landright-twilio-auth-token" "Enter Twilio Auth Token (or press Enter to skip)"
update_secret "landright-twilio-from-number" "Enter Twilio From Number e.g. +15551234567 (or press Enter to skip)"

echo ""
echo "=== DocuSign (E-Signatures) ==="
update_secret "landright-docusign-integration-key" "Enter DocuSign Integration Key (or press Enter to skip)"
update_secret "landright-docusign-secret-key" "Enter DocuSign Secret Key (or press Enter to skip)"

echo ""
echo "=== Summary ==="
echo ""
echo "Auto-generated secrets (no action needed):"
echo "  - landright-db-password"
echo "  - landright-jwt-secret"
echo "  - landright-encryption-key"
echo "  - landright-session-secret"
echo ""
echo "Vertex AI / Gemini:"
echo "  - Uses service account IAM (no API key needed for GCP-hosted services)"
echo ""
echo "To view a secret value:"
echo "  gcloud secrets versions access latest --secret=SECRET_NAME"
echo ""
echo "To update a secret later:"
echo "  echo -n 'NEW_VALUE' | gcloud secrets versions add SECRET_NAME --data-file=-"
echo ""
echo "=== Done ==="
