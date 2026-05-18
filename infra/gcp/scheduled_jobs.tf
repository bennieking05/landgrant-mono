# ------------------------------------------------------------------------------
# Scheduled jobs (Phase 5)
#
# Cloud Scheduler posts to internal Cloud Run endpoints on a cadence so that
# AI invariants (audit chain integrity) and long-running pipelines
# (regulatory monitor, ML training) keep running without a human trigger.
# ------------------------------------------------------------------------------

resource "google_service_account" "scheduler" {
  account_id   = "landgrant-scheduler"
  display_name = "LandGrant Cloud Scheduler invoker"
  project      = var.project_id
}

resource "google_cloud_run_v2_service_iam_member" "scheduler_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}

# Nightly audit hash-chain verification.  ``/audit/chain/verify`` returns
# ``verified: false`` + ``first_bad_event`` when any event has been
# rewritten, which alerts page SRE via log-based alert.
resource "google_cloud_scheduler_job" "audit_chain_verify" {
  name        = "landgrant-audit-chain-verify"
  description = "Verify the audit event hash chain every night"
  schedule    = "15 3 * * *"
  time_zone   = "Etc/UTC"
  project     = var.project_id
  region      = var.region

  http_target {
    http_method = "GET"
    uri         = "${google_cloud_run_v2_service.api.uri}/audit/chain/verify"

    oidc_token {
      service_account_email = google_service_account.scheduler.email
      audience              = google_cloud_run_v2_service.api.uri
    }
  }

  depends_on = [google_cloud_run_v2_service_iam_member.scheduler_invoker]
}

# Regulatory monitor: pulls registered feeds and persists deltas to
# ``regulatory_updates`` / ``law_changes`` (Phase 2.2).
resource "google_cloud_scheduler_job" "regulatory_monitor" {
  name        = "landgrant-regulatory-monitor"
  description = "Run regulatory feed monitor every 6h"
  schedule    = "0 */6 * * *"
  time_zone   = "Etc/UTC"
  project     = var.project_id
  region      = var.region

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.api.uri}/ops/regulatory-monitor/run"

    oidc_token {
      service_account_email = google_service_account.scheduler.email
      audience              = google_cloud_run_v2_service.api.uri
    }
  }

  depends_on = [google_cloud_run_v2_service_iam_member.scheduler_invoker]
}

# Daily ML training loop.  ``run_training_loop`` skips when there aren't
# enough outcomes, so a daily cadence is safe.
resource "google_cloud_scheduler_job" "ml_training" {
  name        = "landgrant-ml-training"
  description = "Kick off settlement model retraining daily"
  schedule    = "30 4 * * *"
  time_zone   = "Etc/UTC"
  project     = var.project_id
  region      = var.region

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.api.uri}/predictions/train"

    oidc_token {
      service_account_email = google_service_account.scheduler.email
      audience              = google_cloud_run_v2_service.api.uri
    }
  }

  depends_on = [google_cloud_run_v2_service_iam_member.scheduler_invoker]
}
