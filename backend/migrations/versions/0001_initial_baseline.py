"""Initial baseline revision.

Creates the full schema from ``app.db.session.Base.metadata``.

For existing environments that previously relied on ``Base.metadata.create_all``
(see ``app/main.py`` dev bootstrap), stamp this revision without running the
DDL::

    alembic stamp 0001_initial_baseline

For fresh environments::

    alembic upgrade head

Revision ID: 0001_initial_baseline
Revises:
Create Date: 2026-04-18

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op  # noqa: F401

from app.db.session import Base


revision: str = "0001_initial_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables declared on ``Base.metadata``.

    We import ``app.db.models`` for its side effect of registering every ORM
    class on the shared ``Base`` before emitting DDL.
    """

    import app.db.models  # noqa: F401

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    import app.db.models  # noqa: F401

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
