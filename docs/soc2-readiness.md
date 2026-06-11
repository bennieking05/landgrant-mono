# SOC 2 readiness index (internal)

LandGrant is **not** SOC 2 certified until an auditor issues an opinion. Do **not** claim SOC 2 in product UI, marketing, or customer decks.

This page links **control evidence** work tracked for Phase 2 hardening:

| Topic | Location |
|-------|----------|
| Security model | [SECURITY.md](./SECURITY.md) |
| Access review export | [compliance/access-review.md](./compliance/access-review.md), `GET /admin/access-review/export` |
| Change management / deploy | [cicd-gcp.md](./cicd-gcp.md#change-management--signed-releases) |
| Incident response | [runbooks/incident.md](./runbooks/incident.md) |
| Vendors & DPAs | [vendors.md](./vendors.md) |
| Demo data policy | [demo-staging.md](./demo-staging.md) |
| Observability (Sentry, logs) | [architecture.md](./architecture.md), [nonfunctional.md](./nonfunctional.md) |
