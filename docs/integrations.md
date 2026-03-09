# Integrations & Credentials

| Capability | Vendor | Notes |
|------------|--------|-------|
| GIS / Parcel basemap | ESRI / ArcGIS Online | OAuth2 service account; feature layers synced nightly. |
| E-sign | Adobe Sign (primary) / Dropbox Sign (backup) | Webhook -> Pub/Sub -> `/integrations/esign` endpoint; documents stored w/ hash. |
| Email | SendGrid | IP warm-up; signed webhooks. |
| SMS | Twilio | Verified toll-free numbers; short-code optional. |
| Certified Mail | Lob (primary) + USPS Web Tools fallback | Delivery proof IDs stored on `Communication`. |
| OCR | AWS Textract or GCP DocAI | Server-side invocation via Celery tasks. |
| Calendar | iCal feed + optional Graph API / Google Calendar push | For deadlines/alerts; tokens stored in Secret Manager. |
| Storage | GCS (`<project>-evidence`) with CMEK | Signed URLs for large uploads. |
| Monitoring | Sentry + Cloud Monitoring + OpenTelemetry Collector | DSNs stored in Secret Manager; traces exported to Cloud Trace. |
| Feature Flags | LaunchDarkly (or open-source Unleash) | Flags used for enabling AI assistance per persona. |

Secrets strategy:
- Stored in Secret Manager; accessed via Workload Identity-enabled K8s ServiceAccounts.
- GitHub Actions uses OIDC to mint short-lived tokens; no static service account keys.
