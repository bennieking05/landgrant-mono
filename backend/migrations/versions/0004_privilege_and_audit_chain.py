"""Privilege, retention, litigation_hold columns + audit chain prev_hash.

Revision ID: 0004_privilege_and_audit_chain
Revises: 0003_firm_tenancy
Create Date: 2026-04-18
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0004_privilege_and_audit_chain"
down_revision: Union[str, None] = "0003_firm_tenancy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("privilege_class", sa.String(), server_default="work_product"),
    )
    op.add_column(
        "documents",
        sa.Column("retention_class", sa.String(), server_default="default"),
    )
    op.add_column("documents", sa.Column("retention_until", sa.DateTime()))
    op.add_column(
        "documents",
        sa.Column("litigation_hold", sa.Boolean(), server_default=sa.text("false")),
    )

    op.add_column("audit_events", sa.Column("firm_id", sa.String(), index=True))
    op.create_foreign_key(
        "fk_audit_events_firm_id", "audit_events", "firms", ["firm_id"], ["id"]
    )
    op.add_column("audit_events", sa.Column("prev_hash", sa.String()))


def downgrade() -> None:
    op.drop_column("audit_events", "prev_hash")
    op.drop_constraint("fk_audit_events_firm_id", "audit_events", type_="foreignkey")
    op.drop_column("audit_events", "firm_id")

    op.drop_column("documents", "litigation_hold")
    op.drop_column("documents", "retention_until")
    op.drop_column("documents", "retention_class")
    op.drop_column("documents", "privilege_class")
