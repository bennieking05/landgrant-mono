# Where the LandGrant portal (SPA) is hosted

The Vite **React app** is **not** served by a Cloud Run service named after `package.json` (`landgrant-frontend`). The production pipeline builds static files and syncs them to **Cloud Storage**, then the **global HTTPS load balancer** (Terraform `frontend.tf`) serves them on your **`app_domain`**.

## Canonical URLs (bookmark these)

| Environment | App (SPA) | Notes |
|-------------|-----------|--------|
| Staging | `https://app-staging.landgrantiq.com` | Override `app_domain` in `infra/gcp/environments/staging.tfvars` if yours differs. |
| Production | `https://app.landgrantiq.com` | Same for `prod.tfvars`. |

The API is on **`api_domain`** (e.g. `https://api-staging.landgrantiq.com`). Marketing / apex uses **`landgrant-marketing`** on Cloud Run (`apex_domain`), not the SPA bucket.

**Do not** use `https://landgrant-frontend-….run.app` (or any stray `*.run.app` URL) as the “real” portal unless you deliberately deploy and maintain that Cloud Run service yourself. The default [`cloudbuild.yaml`](../cloudbuild.yaml) pipeline does **not** update it.

## URLs that will look “stale” or wrong

- **Wrong host** — See above: Cloud Run hosts with similar names are easy to confuse with the product; they are **out of band** for the GCS + LB pipeline.
- **Hard refresh** — `index.html` is deployed with short cache headers; hashed assets under `/assets/` are long-lived. If the UI still looks old right after a deploy, **CDN invalidation** must succeed (see [cicd-gcp.md](./cicd-gcp.md) and [runbooks/cloud-build-cdn-invalidate-iam.md](./runbooks/cloud-build-cdn-invalidate-iam.md)); you can also invalidate manually:

```bash
gcloud compute url-maps invalidate-cdn-cache landgrant-frontend-urlmap \
  --path='/*' --global --project=YOUR_GCP_PROJECT_ID
```

If your Terraform URL map name differs, pass `_FRONTEND_URL_MAP` on `gcloud builds submit` (see `cloudbuild.yaml` substitutions).

## GCS bucket alignment (critical for UX)

Terraform defines the SPA bucket in [`infra/gcp/frontend.tf`](../infra/gcp/frontend.tf) (often ``${project_id}-frontend-<random_hex>``). Cloud Build defaults to ``gs://${_PROJECT_ID}-frontend``. **Those names must match the bucket wired to the load balancer**, or new builds never reach users.

- Full checklist: [runbooks/verify-frontend-bucket-and-cdn.md](./runbooks/verify-frontend-bucket-and-cdn.md)
- After `terraform apply` in `infra/gcp`, append the correct bucket to Cloud Build substitutions using [`infra/gcp/scripts/print-cloudbuild-frontend-substitutions.sh`](../infra/gcp/scripts/print-cloudbuild-frontend-substitutions.sh) (see [cicd-gcp.md](./cicd-gcp.md)).

## Auditing stray `landgrant-frontend` Cloud Run services

List services and confirm nothing production-critical routes to an unexpected host:

```bash
gcloud run services list --project=YOUR_GCP_PROJECT_ID --region=us-central1 \
  --format='table(name,status.url)'
```

If **`landgrant-frontend`** (or similar) is unused, remove it from bookmarks and consider **deleting** the service after DNS and docs point only at **`app_domain`**, so the team is not misled again.

## GCP project ID vs product name

**LandGrant** is the product. Your **GCP project ID** (e.g. `my-company-landgrant-prod`) is what Artifact Registry, GCS, and Cloud Build use. Set **`_PROJECT_ID`** in Cloud Build substitutions to match the project you deploy into (see [cicd-gcp.md](./cicd-gcp.md)).
