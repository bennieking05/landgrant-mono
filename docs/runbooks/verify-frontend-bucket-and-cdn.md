# Verify frontend bucket, LB, and CDN (SPA UX drift)

Use this when the app at **`app_domain`** does not show the latest UI after a deploy.

## 1. Confirm the URL you are testing

The pipeline updates the SPA on **`app_domain`** (see `terraform output frontend_url`), **not** an ad hoc Cloud Run URL such as `https://landgrant-frontend-….run.app`. See [frontend-hosting.md](../frontend-hosting.md).

## 2. Which GCS bucket does the load balancer use?

```bash
PROJECT=<your_gcp_project_id>
gcloud compute backend-buckets list --global --project="${PROJECT}" \
  --filter='name~frontend' --format='table(name,bucketName)'
```

Note **`bucketName`** (the GCS bucket). For LandGrant’s default Terraform name pattern, see `google_compute_backend_bucket.frontend` in [`infra/gcp/frontend.tf`](../../infra/gcp/frontend.tf).

## 3. Does Cloud Build rsync to that bucket?

[`cloudbuild.yaml`](../../cloudbuild.yaml) uses substitution **`_FRONTEND_BUCKET`** (default `${_PROJECT_ID}-frontend`). That **must** match the bucket from step 2.

- **Drift check:** List buckets whose names contain `frontend`:

  ```bash
  gcloud storage buckets list --project="${PROJECT}" --format='value(name)' | grep frontend || true
  ```

  If Terraform created `PROJECT-frontend-<random>` but Cloud Build still uses `PROJECT-frontend`, uploads go to the **wrong** object prefix and the LB will never see new files. Fix by passing **`_FRONTEND_BUCKET`** from Terraform output (use [`infra/gcp/scripts/print-cloudbuild-frontend-substitutions.sh`](../../infra/gcp/scripts/print-cloudbuild-frontend-substitutions.sh)) or align infra (see [frontend-hosting.md](../frontend-hosting.md)).

## 4. CDN invalidation

After `gsutil rsync`, Cloud Build runs **`gcloud compute url-maps invalidate-cdn-cache`** on **`landgrant-frontend-urlmap`** (unless disabled). If the build logs **WARN** on that step, grant the **reserved** Cloud Build service account permission to invalidate (see [cloud-build-cdn-invalidate-iam.md](./cloud-build-cdn-invalidate-iam.md)).

Manual invalidation:

```bash
gcloud compute url-maps invalidate-cdn-cache landgrant-frontend-urlmap \
  --path='/*' --global --project="${PROJECT}" --async
```

## Reference: clearpath-490715 spot check (2026-06)

Backend bucket **`clearpath-490715-frontend-backend`** used GCS name **`clearpath-490715-frontend`**, matching the Cloud Build default **`_FRONTEND_BUCKET=${_PROJECT_ID}-frontend`** for that project. Other `*-frontend-*` buckets may be legacy or non-LB buckets and should be audited before deletion.
