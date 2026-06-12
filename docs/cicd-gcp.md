# GitHub Actions → Google Cloud Build

Pushes to `main` can run [`cloudbuild.yaml`](../cloudbuild.yaml) after tests pass. The workflow job `Deploy (Cloud Build)` in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) uses **Workload Identity Federation** (no long-lived JSON keys).

## 1. Enable the deploy job

In the GitHub repo: **Settings → Secrets and variables → Actions → Variables**

| Variable               | Value   | Purpose                                      |
|------------------------|---------|----------------------------------------------|
| `GCP_DEPLOY_ENABLED`   | `true`  | Turns on the deploy job (default is off).    |
| `GCP_PROJECT_ID`       | optional | Defaults to `clearpath-490715` if unset.   |

## 2. Workload Identity Federation + deploy service account

Follow Google’s guide: [Authenticate to Google Cloud from GitHub Actions](https://cloud.google.com/blog/products/identity-security/enabling-keyless-authentication-from-github-actions).

Summary:

1. Enable APIs: `iamcredentials.googleapis.com`, `sts.googleapis.com`, `cloudbuild.googleapis.com`.
2. Create a **Workload Identity Pool** and **OIDC provider** for GitHub (`attribute.repository`, etc.).
3. Create a **service account** (e.g. `github-deploy@PROJECT_ID.iam.gserviceaccount.com`) used only for CI.
4. Bind **WIF** to that SA: `roles/iam.workloadIdentityUser` on the SA for principal `principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID/attribute.repository/ORG/REPO`.
5. Grant the deploy SA at least:
   - `roles/cloudbuild.builds.editor` — create builds
   - `roles/storage.objectUser` (or scoped access) — upload build source to `gs://PROJECT_ID_cloudbuild/source/`
   - `roles/serviceusage.serviceUsageConsumer` — often included via Editor; ensure API usage is allowed

`gcloud builds submit` still runs build steps under the project’s **Cloud Build service identity** (typically `{project_number}@cloudbuild.gserviceaccount.com` unless you configure a custom build SA). Artifact Registry and Cloud Run IAM for those identities are separate (see project setup and [runbooks/cloud-build-cdn-invalidate-iam.md](./runbooks/cloud-build-cdn-invalidate-iam.md)).

## 3. GitHub repository secrets

**Settings → Secrets and variables → Actions → Secrets**

| Secret                           | Example value |
|----------------------------------|---------------|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `GCP_DEPLOY_SERVICE_ACCOUNT`      | `github-deploy@clearpath-490715.iam.gserviceaccount.com` |

### Provisioned for `clearpath-490715` (Workload Identity pool `github-pool`)

These values are live in GCP. Add them as repository secrets (or use the [`gh`](https://cli.github.com/) commands below after `gh auth login`).

| Secret | Value |
|--------|--------|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/616827239777/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `GCP_DEPLOY_SERVICE_ACCOUNT` | `github-deploy@clearpath-490715.iam.gserviceaccount.com` |

The OIDC provider uses an **attribute condition** so only the GitHub repository **`bennieking05/landgrant-mono`** can obtain tokens. If the repo is renamed or forked under another path, update the provider condition in GCP or add a matching binding.

**Enable deploy** (repository **variable**, not secret):

```bash
gh variable set GCP_DEPLOY_ENABLED --body true --repo bennieking05/landgrant-mono
```

**Set secrets** (from repo root, after `gh auth login`):

```bash
printf '%s' 'projects/616827239777/locations/global/workloadIdentityPools/github-pool/providers/github-provider' | gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER --repo bennieking05/landgrant-mono
printf '%s' 'github-deploy@clearpath-490715.iam.gserviceaccount.com' | gh secret set GCP_DEPLOY_SERVICE_ACCOUNT --repo bennieking05/landgrant-mono
```

## 4. Manual submit (local)

From repo root (same as CI). **`--project` and `_PROJECT_ID` must match** so images, buckets, and `gcloud run` calls target the same LandGrant GCP project:

```bash
PROJECT="$(gcloud config get-value project)"
COMMIT_SHA="$(git rev-parse HEAD)"
EXTRA="$(infra/gcp/scripts/print-cloudbuild-frontend-substitutions.sh || true)"
gcloud builds submit . \
  --config=cloudbuild.yaml \
  --project="${PROJECT}" \
  --substitutions="COMMIT_SHA=${COMMIT_SHA},_PROJECT_ID=${PROJECT}${EXTRA}"
```

`EXTRA` appends `,_FRONTEND_BUCKET=<terraform bucket>` when [`infra/gcp/scripts/print-cloudbuild-frontend-substitutions.sh`](../infra/gcp/scripts/print-cloudbuild-frontend-substitutions.sh) can read Terraform state (run from repo root after `terraform apply` in `infra/gcp`). If the script prints nothing, confirm the default bucket matches the load balancer (see [runbooks/verify-frontend-bucket-and-cdn.md](./runbooks/verify-frontend-bucket-and-cdn.md)).

If your frontend bucket name is not ``${PROJECT}-frontend`` (for example Terraform used a random suffix), you **must** pass **`_FRONTEND_BUCKET`** explicitly (script output or console value).

After deploy, open the SPA at your **`app_domain`** (see [frontend-hosting.md](./frontend-hosting.md)), not an unrelated `*.run.app` host unless you intentionally serve the SPA there.

### CDN invalidation (Cloud Build)

The build runs `gcloud compute url-maps invalidate-cdn-cache` on **`landgrant-frontend-urlmap`** by default so users see new JS/CSS quickly. Build steps run as Google’s **reserved** Cloud Build SA `{project_number}@cloudbuild.gserviceaccount.com` (not necessarily `landgrant-cloudbuild@…`). Grant that identity permission to invalidate caches (Terraform default `grant_reserved_cloudbuild_cdn_invalidation`, or manual steps in [runbooks/cloud-build-cdn-invalidate-iam.md](./runbooks/cloud-build-cdn-invalidate-iam.md)). If invalidation fails, the build logs a **WARN** but still succeeds; origin objects in GCS are already updated.

## Database migrations

- **Cloud Run API (`landgrant-api`)** sets `ALEMBIC_AUTO=true` (see `infra/gcp/cloudrun.tf`). On each container start, the FastAPI lifespan runs `alembic upgrade head` against the configured database before serving traffic. That covers routine releases when the API can reach Cloud SQL (same VPC / private IP path as production).
- **Manual `alembic upgrade head`** (from a workstation with Cloud SQL Auth Proxy, Cloud Shell on a VPC-attached VM, etc.) is still valid for one-off repairs, backfills, or if you ever disable `ALEMBIC_AUTO`.
- **Verify revision** (optional): connect to the instance and `SELECT version_num FROM alembic_version;` — expect `0007_parcel_grid_saved_views` at head for current rule packs.

### Optional: pipeline-only migrations (future)

If you want migrations **decoupled** from API startup (faster cold starts, stricter change windows, or `ALEMBIC_AUTO=false`):

1. **Cloud Run Job** — image reuse of `landgrant/api`, same env/secrets as the API service, command `alembic upgrade head` (or `python -m alembic upgrade head`), VPC egress to Cloud SQL, IAM `roles/cloudsql.client` on the job SA. Trigger the job from Cloud Build after `deploy-api` and before traffic shift, or on a schedule.
2. **Cloud Build step** — a step that runs the API image with `DATABASE_URL` / connector flags and runs Alembic; requires granting the Cloud Build service account access to Cloud SQL (often via VPC-enabled worker pool or Cloud SQL Auth Proxy sidecar pattern).

Prefer the **job** pattern for least coupling to build VMs and clearer audit logs.

## Frontend `VITE_API_BASE` and staging E2E

[`cloudbuild.yaml`](../cloudbuild.yaml) resolves the **live** Cloud Run URL with `gcloud run services describe landgrant-api … --format='value(status.url)'` and passes it into `npm run build`. That matches the hostname browsers and Playwright use.

GitHub Actions [`.github/workflows/staging-e2e.yml`](../.github/workflows/staging-e2e.yml) expects `STAGING_API_BASE_URL` to match that same API origin. After changing regions or service names, update the repository secret if it was hand-maintained.

## Centralized logs and retention

Application logs ship to **Google Cloud Logging** with Cloud Run default retention. Adjust retention and export sinks in Terraform (`infra/gcp/`) per your compliance calendar. Restrict log viewer roles to least privilege.

## Change management and signed releases

- **Default branch**: merges to `main` only via pull request with required checks (`landgrant-ci`).
- **Production deploy**: optional Cloud Build deploy job in CI runs after `validate`, `playwright`, and `staging_e2e` (skipped on non-tag pushes; for `v*` tags configure staging secrets or the job exits successfully when secrets are absent).
- **Releases**: GitHub **Releases** should tag immutable SHAs. Prefer [artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations) or image signing (Cosign) before claiming supply-chain controls in customer questionnaires.

See also [soc2-readiness.md](./soc2-readiness.md) (internal index, not a SOC 2 opinion).
