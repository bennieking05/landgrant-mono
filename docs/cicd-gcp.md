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

`gcloud builds submit` still runs build steps under the project’s **Cloud Build service identity** (e.g. default Compute SA); Artifact Registry and Cloud Run IAM for those identities are separate (see project setup).

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

From repo root (same as CI):

```bash
gcloud builds submit . \
  --config=cloudbuild.yaml \
  --project=clearpath-490715 \
  --substitutions="COMMIT_SHA=$(git rev-parse HEAD)"
```

`COMMIT_SHA` must be set for image tags; CI passes `GITHUB_SHA`.
