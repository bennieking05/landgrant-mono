# Vendor Inventory

| Vendor | Purpose | DPA Status | Notes |
|--------|---------|-----------|-------|
| ESRI / ArcGIS | Parcel basemaps + geospatial layers | Pending | OAuth app + service account. |
| Adobe Sign | Primary e-signature flows | Signed | Webhooks to Pub/Sub. |
| Dropbox Sign | Backup e-sign vendor | Draft | Feature-flag controlled. |
| SendGrid | Outbound email | Signed | Dedicated IP warmup. |
| Twilio | SMS notifications | Signed | Toll-free verification in progress. |
| Lob | Certified mail | Pending | Stores PDF and tracking number. |
| USPS Web Tools | Backup certified mail | Pending | Requires DMZ IP allowlist. |
| AWS Textract | OCR for title/appraisal | Signed | Invoked via Private Service Connect. |
| GCP DocAI | OCR alternative | Signed | Lives in same project; locked to workers. |
| LaunchDarkly | Feature flags | Signed | Flag change events logged. |
| Sentry | Error monitoring | Signed | Uses relay to avoid PII egress. |
