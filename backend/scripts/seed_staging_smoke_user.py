"""Create the staging smoke-test login.

Run only in staging:

    ENVIRONMENT=staging python -m scripts.seed_staging_smoke_user
"""

from __future__ import annotations

from passlib.context import CryptContext

from app.core.config import get_settings
from app.db import models
from app.db.session import Base, SessionLocal, engine


SMOKE_EMAIL = "staging-smoke@landgrant.local"
SMOKE_PASSWORD = "devpass123"


def seed_staging_smoke_user() -> None:
    settings = get_settings()
    if settings.environment != "staging":
        raise SystemExit(
            f"seed_staging_smoke_user: refuse environment={settings.environment!r}"
        )

    Base.metadata.create_all(bind=engine)

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

        user = db.query(models.User).filter(models.User.email == SMOKE_EMAIL).first()
        password_hash = CryptContext(schemes=["bcrypt"], deprecated="auto").hash(
            SMOKE_PASSWORD
        )
        if user:
            user.password_hash = password_hash
            user.persona = models.Persona.PLATFORM_ADMIN
            user.firm_id = models.DEFAULT_FIRM_ID
            user.full_name = "Staging Smoke"
        else:
            db.add(
                models.User(
                    id="STAGING-SMOKE-001",
                    email=SMOKE_EMAIL,
                    persona=models.Persona.PLATFORM_ADMIN,
                    full_name="Staging Smoke",
                    firm_id=models.DEFAULT_FIRM_ID,
                    password_hash=password_hash,
                )
            )
        db.commit()
        print(f"seed_staging_smoke_user: ready {SMOKE_EMAIL}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_staging_smoke_user()
