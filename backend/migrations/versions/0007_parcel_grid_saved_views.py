"""Parcel grid saved views (per-user filters for workbench UX-4).

Revision ID: 0007_parcel_grid_saved_views
Revises: 0006_contract_schema_reconcile
Create Date: 2026-06-11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0007_parcel_grid_saved_views"
down_revision: Union[str, None] = "0006_contract_schema_reconcile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parcel_grid_saved_views",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_parcel_grid_saved_views_user_name"),
    )
    op.create_index(
        "ix_parcel_grid_saved_views_user_id",
        "parcel_grid_saved_views",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_parcel_grid_saved_views_user_id", table_name="parcel_grid_saved_views")
    op.drop_table("parcel_grid_saved_views")
