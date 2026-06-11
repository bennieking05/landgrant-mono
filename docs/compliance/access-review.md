# Access review (SOC2 readiness)

**Not** a SOC 2 report. Use this runbook for quarterly access reviews until an auditor is engaged.

## Export

Platform admins can export current users and roles:

- `GET /admin/access-review/export?fmt=csv`
- `GET /admin/access-review/export?fmt=json`

Requires JWT with `platform_admin` and `admin_platform` read (see `backend/app/api/routes/admin.py`).

## Procedure (suggested quarterly)

1. Download CSV from staging or production admin tooling (use a break-glass admin account).
2. Compare against HR / IdP roster for active employees and contractors.
3. Revoke or downgrade personas for departed users; document exceptions.
4. Store the signed CSV in your evidence store with date and reviewer name.
