# Deploy Runbook

1. Merge PR into `main`.
2. **CI/CD:** GitHub Actions runs tests, then (if enabled) submits [`cloudbuild.yaml`](../cloudbuild.yaml) to Cloud Build. That builds container images, deploys Cloud Run services (`landright-api`, `landright-worker`, `landright-marketing`), and syncs the Vite frontend to the GCS bucket. Configure GitHub variables/secrets per [cicd-gcp.md](../cicd-gcp.md).
3. **Manual:** From repo root, `gcloud builds submit` with `--substitutions=COMMIT_SHA=$(git rev-parse HEAD)` (see [cicd-gcp.md](../cicd-gcp.md)).
4. Monitor Cloud Build in the GCP console; verify Cloud Run revisions and `/health` endpoints as needed.
5. Verify health checks + synthetic monitors.
