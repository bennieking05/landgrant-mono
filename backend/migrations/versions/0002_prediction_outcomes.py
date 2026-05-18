"""Add ``prediction_outcomes`` table.

Revision ID: 0002_prediction_outcomes
Revises: 0001_initial_baseline
Create Date: 2026-04-18
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0002_prediction_outcomes"
down_revision: Union[str, None] = "0001_initial_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prediction_outcomes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("prediction_id", sa.String(), nullable=False, index=True),
        sa.Column("parcel_id", sa.String(), sa.ForeignKey("parcels.id")),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id")),
        sa.Column("jurisdiction", sa.String()),
        sa.Column("model_used", sa.String(), server_default="rules"),
        sa.Column("input_features", sa.JSON()),
        sa.Column("predicted_settlement", sa.Numeric()),
        sa.Column("predicted_low", sa.Numeric()),
        sa.Column("predicted_high", sa.Numeric()),
        sa.Column("predicted_confidence", sa.Numeric()),
        sa.Column("actual_settlement", sa.Numeric()),
        sa.Column("went_to_litigation", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("days_to_settlement", sa.Integer()),
        sa.Column("prediction_date", sa.DateTime()),
        sa.Column("outcome_date", sa.DateTime()),
        sa.Column("created_at", sa.DateTime()),
    )


def downgrade() -> None:
    op.drop_table("prediction_outcomes")
