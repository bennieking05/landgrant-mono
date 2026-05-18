"""Add ``firms`` table and ``firm_id`` FK on tenant-scoped tables.

Revision ID: 0003_firm_tenancy
Revises: 0002_prediction_outcomes
Create Date: 2026-04-18
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0003_firm_tenancy"
down_revision: Union[str, None] = "0002_prediction_outcomes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_FIRM_ID = "firm_default"


def upgrade() -> None:
    op.create_table(
        "firms",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), unique=True, index=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("metadata_json", sa.JSON()),
        sa.Column("created_at", sa.DateTime()),
    )

    for table in ("projects", "users", "documents"):
        op.add_column(
            table,
            sa.Column("firm_id", sa.String(), nullable=True, index=True),
        )
        op.create_foreign_key(
            f"fk_{table}_firm_id",
            table,
            "firms",
            ["firm_id"],
            ["id"],
        )

    # Seed default firm row and backfill scoped tables so the upgrade is safe.
    op.execute(
        sa.text(
            "INSERT INTO firms (id, name, slug, active) "
            "VALUES (:id, :name, :slug, true) "
            "ON CONFLICT DO NOTHING"
        ).bindparams(id=DEFAULT_FIRM_ID, name="Default Firm", slug=DEFAULT_FIRM_ID)
    )
    for table in ("projects", "users", "documents"):
        op.execute(
            sa.text(
                f"UPDATE {table} SET firm_id = :firm_id WHERE firm_id IS NULL"
            ).bindparams(firm_id=DEFAULT_FIRM_ID)
        )


def downgrade() -> None:
    for table in ("projects", "users", "documents"):
        op.drop_constraint(f"fk_{table}_firm_id", table, type_="foreignkey")
        op.drop_column(table, "firm_id")
    op.drop_table("firms")
