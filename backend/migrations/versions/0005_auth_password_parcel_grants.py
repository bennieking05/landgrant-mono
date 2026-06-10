"""Add user password hashes and parcel_access_grants for row-level scope.

Revision ID: 0005_auth_password_parcel_grants
Revises: 0004_privilege_and_audit_chain
Create Date: 2026-06-10
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0005_auth_password_parcel_grants"
down_revision: Union[str, None] = "0004_privilege_and_audit_chain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )
    op.create_table(
        "parcel_access_grants",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("parcel_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("grantee_email", sa.String(), nullable=True),
        sa.Column("scope_persona", sa.String(length=64), nullable=False),
        sa.Column("firm_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"]),
        sa.ForeignKeyConstraint(["parcel_id"], ["parcels.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_parcel_access_grants_parcel_id",
        "parcel_access_grants",
        ["parcel_id"],
        unique=False,
    )
    op.create_index(
        "ix_parcel_access_grants_user_id",
        "parcel_access_grants",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_parcel_access_grants_grantee_email",
        "parcel_access_grants",
        ["grantee_email"],
        unique=False,
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Persona enum on users/tasks/etc. — extend for platform_admin.
        op.execute(
            sa.text(
                "ALTER TYPE persona ADD VALUE IF NOT EXISTS 'platform_admin'"
            )
        )


def downgrade() -> None:
    op.drop_index("ix_parcel_access_grants_grantee_email", table_name="parcel_access_grants")
    op.drop_index("ix_parcel_access_grants_user_id", table_name="parcel_access_grants")
    op.drop_index("ix_parcel_access_grants_parcel_id", table_name="parcel_access_grants")
    op.drop_table("parcel_access_grants")
    op.drop_column("users", "password_hash")
