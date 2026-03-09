#!/bin/bash
# ------------------------------------------------------------------------------
# List all LandRight secrets and their status
# ------------------------------------------------------------------------------

PROJECT_ID="landright-483916"

echo "=== LandRight Secrets in Secret Manager ==="
echo "Project: ${PROJECT_ID}"
echo ""

gcloud secrets list --project="${PROJECT_ID}" --filter="labels.app=landright" \
    --format="table(name.basename(), createTime.date('%Y-%m-%d'), labels)"

echo ""
echo "=== Secret Details ==="
echo ""

for secret in $(gcloud secrets list --project="${PROJECT_ID}" --filter="labels.app=landright" --format="value(name)"); do
    secret_name=$(basename $secret)
    version_count=$(gcloud secrets versions list "$secret_name" --project="${PROJECT_ID}" --format="value(name)" | wc -l | tr -d ' ')
    latest_version=$(gcloud secrets versions list "$secret_name" --project="${PROJECT_ID}" --limit=1 --format="value(name)")
    
    # Check if it's a placeholder
    value=$(gcloud secrets versions access latest --secret="$secret_name" --project="${PROJECT_ID}" 2>/dev/null || echo "ERROR")
    if [[ "$value" == "PLACEHOLDER"* ]] || [[ "$value" == "USE_SERVICE"* ]] || [[ "$value" == "+1XXXX"* ]]; then
        status="⚠️  PLACEHOLDER"
    elif [[ "$value" == "ERROR" ]]; then
        status="❌ ERROR"
    else
        status="✓ Configured"
    fi
    
    printf "%-40s %s (v%s, %d versions)\n" "$secret_name" "$status" "$latest_version" "$version_count"
done

echo ""
echo "To update a secret:"
echo "  echo -n 'value' | gcloud secrets versions add SECRET_NAME --data-file=-"
