"""Idempotent demo tenant seed for staging sales demos (Phase 2).

Creates default firm (if missing), one ``DEMO-STAGING`` project, and one parcel.
**Only** when ``ENVIRONMENT=staging`` — refuses dev/test/prod.

Run after migrations::

    ENVIRONMENT=staging DATABASE_URL=... python -m scripts.seed_demo_tenant

See ``docs/demo-staging.md``.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.core.config import get_settings
from app.db import models
from app.db.session import SessionLocal


DEMO_PROJECT_ID = "DEMO-STAGING-001"
DEMO_PARCEL_ID = "DEMO-STAGING-P001"


def seed_demo_tenant() -> None:
    settings = get_settings()
    if settings.environment != "staging":
        raise SystemExit(
            f"seed_demo_tenant: refuse environment={settings.environment!r} "
            "(only staging is allowed)"
        )

    db = SessionLocal()
    try:
        if not db.get(models.Firm, models.DEFAULT_FIRM_ID):
            db.add(
                models.Firm(
                    id=models.DEFAULT_FIRM_ID,
                    name="Demo Firm (Staging)",
                    slug=models.DEFAULT_FIRM_ID,
                    active=True,
                )
            )
            db.flush()

        if db.get(models.Project, DEMO_PROJECT_ID):
            print("seed_demo_tenant: already seeded")
            return

        proj = models.Project(
            id=DEMO_PROJECT_ID,
            firm_id=models.DEFAULT_FIRM_ID,
            name="Highway 281 Expansion (Demo)",
            jurisdiction_code="TX",
            state="TX",
            project_type="highway",
            operational_status="planning",
            stage=models.ProjectStage.INTAKE,
            risk_score=25,
            next_deadline_at=datetime.utcnow() + timedelta(days=30),
        )
        db.add(proj)
        db.add(
            models.Parcel(
                id=DEMO_PARCEL_ID,
                project_id=DEMO_PROJECT_ID,
                county_fips="48029",
                parcel_number="DEMO-001",
                county="Bexar County",
                parcel_state="TX",
                stage=models.ParcelStage.INTAKE,
                risk_score=40,
            )
        )
        db.commit()
        print("seed_demo_tenant: created demo project", DEMO_PROJECT_ID)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_tenant()
