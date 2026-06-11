# Staging demo tenant (sales)

Demo content (e.g. **Highway 281 Expansion**) must exist **only** on staging, never in production.

## Seed the demo tenant

Requires `ENVIRONMENT=staging` and a migrated database:

```bash
cd backend
export ENVIRONMENT=staging
export DATABASE_URL='postgresql+psycopg://USER:PASS@HOST:5432/landgrant'
python -m scripts.seed_demo_tenant
```

The script is idempotent: it creates `DEMO-STAGING-001` and one parcel if missing.

## Reproducible demo checklist

1. Apply Terraform for staging (`infra/gcp/environments/staging.tfvars`) to an isolated project or instance names.
2. Run migrations (`alembic upgrade head` on deploy or startup per `docs/architecture.md`).
3. Run `seed_demo_tenant` once per fresh staging DB (or after intentional wipe).
4. Create staff users in Auth / admin UI; store passwords in your team vault (e.g. 1Password), not in git.
5. Open the staging SPA URL and sign in; confirm the demo project appears in workbench selectors.

## Production

`ENVIRONMENT=prod` refuses `seed_demo_tenant`. Production must contain **zero** demo seed rows.
