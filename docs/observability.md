# Observability Plan

- **Metrics**: Exported via Prometheus + Cloud Monitoring. Key SLOs: API latency, ingestion rate, binder errors, queue depth, e-sign latency, deadline miss count.
- **Traces**: OTLP exporter configured in `app/telemetry.py` sending to Cloud Trace via OTLP HTTP.
- **Logs**: FastAPI structured logs -> Cloud Logging -> BigQuery; includes request_id + persona for auditing.
- **Dashboards**: Terraform-managed (see `infra/gcp/main.tf`). Additional JSON definitions stored under `infra/gcp/dashboards/`.
- **Alerts**: Notification channel variable `alert_notification_channel` ties to PagerDuty/Email. Policies for SLO burn, task queue backlog, webhook failures.
- **Synthetic Monitors**: `/health/live`, `/health/invite`, `/health/esign` plus new docket webhook check triggered by Cloud Scheduler.
