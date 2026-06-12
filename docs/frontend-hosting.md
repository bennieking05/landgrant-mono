# Where the LandGrant portal (SPA) is hosted

The Vite **React app** is **not** served by a Cloud Run service named after `package.json` (`landgrant-frontend`). The production pipeline builds static files and syncs them to **Cloud Storage**, then the **global HTTPS load balancer** (Terraform `frontend.tf`) serves them on your **`app_domain`**.

## Canonical URLs (from Terraform `app_domain`)

| Environment | App (SPA) | Notes |
|-------------|-----------|--------|
| Staging | `https://app-staging.landgrantiq.com` | Override `app_domain` in `infra/gcp/environments/staging.tfvars` if yours differs. |
| Production | `https://app.landgrantiq.com` | Same for `prod.tfvars`. |

The API is on **`api_domain`** (e.g. `https://api-staging.landgrantiq.com`). Marketing / apex uses **`landgrant-marketing`** on Cloud Run (`apex_domain`), not the SPA bucket.

## URLs that will look “stale” or wrong

- **`https://landgrant-frontend-….run.app`** — If this Cloud Run service exists in your project, it is **not** updated by [`cloudbuild.yaml`](../cloudbuild.yaml). That URL can show an old build or a one-off image. **Use the `app_domain` URL above** after each deploy.
- **Hard refresh** — `index.html` is deployed with short cache headers; hashed assets under `/assets/` are long-lived. If the UI still looks old right after a deploy, **CDN invalidation** should run (see [cicd-gcp.md](./cicd-gcp.md)); you can also invalidate manually:

```bash
gcloud compute url-maps invalidate-cdn-cache landgrant-frontend-urlmap \
  --path='/*' --global --project=YOUR_GCP_PROJECT_ID
```

If your Terraform URL map name differs, pass `_FRONTEND_URL_MAP` on `gcloud builds submit` (see `cloudbuild.yaml` substitutions).

## GCS bucket name

Terraform (`infra/gcp/frontend.tf`) may create the bucket as ``${project_id}-frontend-<random_hex>``. If that does not match ``${_PROJECT_ID}-frontend`` in Cloud Build, override **`_FRONTEND_BUCKET`** when submitting the build (use `terraform output` / the bucket name shown in the console).

## GCP project ID vs product name

**LandGrant** is the product. Your **GCP project ID** (e.g. `my-company-landgrant-prod`) is what Artifact Registry, GCS, and Cloud Build use. Set **`_PROJECT_ID`** in Cloud Build substitutions to match the project you deploy into (see [cicd-gcp.md](./cicd-gcp.md)).
