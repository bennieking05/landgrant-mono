# Environments & Operations

## Environments
- **dev**: Rapid iteration, seeded fixtures (5 projects × 50 parcels × 3 jurisdictions). Feature flags default ON.
- **staging**: Parity with prod; QA + UAT; synthetic monitors run continuously.
- **prod**: Locked down, break-glass role, privileged actions logged + mirrored to SIEM.

## Runbooks
- `deploy.md`: rolling deploy via GitHub Actions -> GKE.
- `rollback.md`: uses previous container tag; Terraform state revert tagged.
- `incident.md`: severity matrix, on-call rotation, comms templates, postmortem template.
- `backup.md`: quarterly restore drill, Cloud SQL PITR verification, binder sample restore.

## Observability
- OpenTelemetry Collector DaemonSet on GKE exports to Cloud Trace & Prometheus.
- Metrics: request latency, Celery queue depth, rule evaluation success, e-sign webhook latency, deadline miss count.
- Logs: structured JSON w/ correlation IDs.

## Operations Calendar
- Weekly: dependency updates, SLO review.
- Monthly: vendor DPA check, security patch rollup.
- Quarterly: rules review (Alicia), backup drill, DR tabletop.
