# Project Governance

- **Repository Layout**: Mono-repo for dev; production split into `/frontend`, `/backend`, `/infra`, `/rules`, `/templates` repos once stable. Until then, maintain directories here.
- **Branching**: `main` protected; feature branches require CI green + reviewer approvals (counsel + engineering for legal-impacting changes).
- **Release Cadence**: Bi-weekly GA releases; emergency hotfix path with after-action review.
- **Change Control**: PR template captures scope, risk, tests, migrations. Legal-impacting PRs require Alicia’s approval + changelog entry.
- **Versioning**: Semantic versioning for app, rules (per jurisdiction), templates, and APIs (OpenAPI doc version).
- **Decision Log**: ADRs stored under `docs/adr/`.
- **Pilot Governance**: Steering committee (Product, Eng, Legal) meets weekly; issues logged in shared tracker.
