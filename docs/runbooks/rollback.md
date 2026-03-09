# Rollback Runbook

1. Identify failing release tag (e.g., `api-2025.11.21.1`).
2. `kubectl rollout undo deployment/api --to-revision=<prev>` or apply prior manifest.
3. For DB migrations, run Alembic downgrade script (stored in release assets).
4. Terraform rollback: re-run last successful plan with `-refresh-only` to verify infra not drifted.
5. Post-rollback validation: smoke tests, synthetic monitors, review error budget impact.
