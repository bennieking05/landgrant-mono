# Deploy Runbook

1. Merge PR into `main`.
2. GitHub Actions build step pushes images to Artifact Registry (`landright` repo).
3. Workflow authenticates to GKE via Workload Identity and runs `kubectl apply -k k8s/overlays/<env>`.
4. Monitor rollout via `kubectl get rollout` (Argo) or `kubectl rollout status`.
5. Verify health checks + synthetic monitors.
