#!/usr/bin/env bash
# Print Cloud Build substitution fragment so gsutil rsync targets the same GCS
# bucket Terraform attaches to the load balancer:
#   terraform output -raw frontend_bucket
#
# Usage (after terraform apply in infra/gcp):
#   COMMIT_SHA=$(git rev-parse HEAD)
#   PROJECT=$(gcloud config get-value project)
#   EXTRA=$(infra/gcp/scripts/print-cloudbuild-frontend-substitutions.sh)
#   gcloud builds submit . --config=cloudbuild.yaml --project="${PROJECT}" \
#     --substitutions="COMMIT_SHA=${COMMIT_SHA},_PROJECT_ID=${PROJECT}${EXTRA}"
#
# Prints nothing (exit 0) if terraform output is unavailable; caller may rely
# on default _FRONTEND_BUCKET=${_PROJECT_ID}-frontend when it matches the live LB bucket.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${TF_ROOT}"

if ! terraform output -raw frontend_bucket &>/dev/null; then
  echo "WARN: terraform output frontend_bucket failed (cd ${TF_ROOT} && terraform init)." >&2
  echo "       Using Cloud Build default _FRONTEND_BUCKET only if it matches the LB bucket (see docs/runbooks/verify-frontend-bucket-and-cdn.md)." >&2
  exit 0
fi

BUCKET="$(terraform output -raw frontend_bucket)"
echo ",_FRONTEND_BUCKET=${BUCKET}"
