# Security & Compliance

- **Access Mgmt**: SSO via Google Workspace/Okta; MFA enforced. Break-glass accounts require pager approval.
- **RBAC**: Implemented in Postgres row-level policies + FastAPI dependency injection (see `backend/app/security/rbac.py`). Least privilege defaults per persona.
- **Audit Logging**: Every CRUD + rule override recorded in `AuditEvent` with `who/what/when/hash`. Logs streamed to Cloud Logging + BigQuery for retention (7 years) and litigation hold.
- **Change Mgmt**: PR templates require risk statements, test evidence, and sign-off for high-risk features. Releases tagged semantically; Terraform changes tracked in plan artifacts.
- **Vendor Risk**: DPAs collected for ArcGIS, Adobe/Dropbox, SendGrid, Twilio, Lob, AWS/GCP OCR, LaunchDarkly. Inventory tracked in `docs/vendors.md`.
- **Crypto**: TLS 1.2+ external, mTLS optional for internal services. CMEK via Cloud KMS. Each export hashed (SHA-256) and stored alongside binder.
- **Backups**: Cloud SQL point-in-time recovery; GCS object versioning; quarterly restore drills documented in `docs/ops.md`.
- **Incident Response**: PagerDuty rotation; runbook includes detection, containment, comms templates, and after-action tasks.
- **Privacy**: Portal banner (“Decision-support only, not legal advice”). PII classification tags; retention configurable per object.
