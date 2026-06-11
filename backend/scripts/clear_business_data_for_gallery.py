"""Truncate business tables for Playwright empty-state gallery (Phase 2).

Preserves ``users``, ``firms``, and ``alembic_version``. Only ``dev`` or ``test``
environment — refuses prod/staging to avoid accidents.

Usage::

    cd backend && CLEAR_GALLERY_DB=1 python -m scripts.clear_business_data_for_gallery

"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.core.config import get_settings
from app.db.session import engine

KEEP = frozenset({"users", "firms", "alembic_version"})


def main() -> None:
    settings = get_settings()
    if settings.environment not in ("dev", "test"):
        raise SystemExit(
            f"refusing to truncate: environment={settings.environment!r} "
            "(allowed: dev, test)"
        )
    insp = inspect(engine)
    dialect = engine.dialect.name
    if dialect == "sqlite":
        names = [t for t in insp.get_table_names() if t not in KEEP]
    else:
        names = [t for t in insp.get_table_names(schema="public") if t not in KEEP]
    if not names:
        print("clear_business_data_for_gallery: no tables to truncate")
        return
    quoted = ", ".join(f'"{n}"' for n in names)
    sql = text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE")
    with engine.begin() as conn:
        conn.execute(sql)
    print(f"clear_business_data_for_gallery: truncated {len(names)} tables")


if __name__ == "__main__":
    main()
