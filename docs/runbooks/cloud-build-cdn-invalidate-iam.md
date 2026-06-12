# IAM: Cloud Build CDN invalidation (`urlMaps.invalidateCache`)

[`cloudbuild.yaml`](../../cloudbuild.yaml) runs `gcloud compute url-maps invalidate-cdn-cache` after uploading the SPA so **Cloud CDN** does not keep serving old hashed assets.

## Which service account runs build steps?

Unless you set a custom service account on the build, Google Cloud Build runs steps as the **reserved** project service account:

`{PROJECT_NUMBER}@cloudbuild.gserviceaccount.com`

This is **not** the same as the Terraform-managed `landgrant-cloudbuild@…` service account in [`infra/gcp/iam.tf`](../../infra/gcp/iam.tf) (that SA is for other automation patterns unless you wire Cloud Build to use it explicitly).

## Terraform (recommended)

When `grant_reserved_cloudbuild_cdn_invalidation` is `true` (default in [`infra/gcp/variables.tf`](../../infra/gcp/variables.tf)), Terraform grants that reserved SA **`roles/compute.loadBalancerAdmin`**, which includes `compute.urlMaps.invalidateCache`. Apply with your environment tfvars, then re-run a Cloud Build; the invalidate step should stop logging **WARN**.

Set `grant_reserved_cloudbuild_cdn_invalidation = false` in tfvars if your org forbids this role; then invalidate manually after each frontend deploy (see [verify-frontend-bucket-and-cdn.md](./verify-frontend-bucket-and-cdn.md)).

## Manual `gcloud` (one-off)

```bash
PROJECT=<your_gcp_project_id>
NUM="$(gcloud projects describe "${PROJECT}" --format='value(projectNumber)')"
gcloud projects add-iam-policy-binding "${PROJECT}" \
  --member="serviceAccount:${NUM}@cloudbuild.gserviceaccount.com" \
  --role="roles/compute.loadBalancerAdmin" \
  --condition=None
```

Use a **custom IAM role** with only `compute.urlMaps.invalidateCache` if your security team requires least privilege (not documented here by default).
