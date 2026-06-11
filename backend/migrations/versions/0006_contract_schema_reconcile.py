"""Contract schema reconciliation (Phase 1): new tables + additive columns.

Preserves Phase 0 auth/tenancy (firms, users.persona, parcel_access_grants) and
string primary keys. Adds contracted domain tables and nullable columns for
backward compatibility with existing rows.

Revision ID: 0006_contract_schema_reconcile
Revises: 0005_auth_password_parcel_grants
Create Date: 2026-06-11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0006_contract_schema_reconcile"
down_revision: Union[str, None] = "0005_auth_password_parcel_grants"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_table_if_missing(bind, table_name: str, *elements) -> None:
    """Skip when SQLAlchemy ``create_all`` already created the table (dev DB)."""

    from sqlalchemy import inspect

    if inspect(bind).has_table(table_name):
        return
    create_table = op.create_table
    create_table(table_name, *elements)


def _column_exists(bind, table: str, column_name: str) -> bool:
    from sqlalchemy import inspect

    return any(
        c["name"] == column_name for c in inspect(bind).get_columns(table)
    )


def _try_add_column(table: str, column: sa.Column) -> None:
    bind = op.get_bind()
    if _column_exists(bind, table, column.name):
        return
    op.add_column(table, column)


def _fk_exists(bind, table: str, fk_name: str) -> bool:
    from sqlalchemy import inspect

    for fk in inspect(bind).get_foreign_keys(table):
        if fk.get("name") == fk_name:
            return True
    return False


def _try_create_fk(
    constraint_name: str,
    source_table: str,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
    **kw: object,
) -> None:
    bind = op.get_bind()
    if _fk_exists(bind, source_table, constraint_name):
        return
    op.create_foreign_key(
        constraint_name,
        source_table,
        referent_table,
        local_cols,
        remote_cols,
        **kw,
    )


def _index_exists(bind, table: str, index_name: str) -> bool:
    from sqlalchemy import inspect

    for ix in inspect(bind).get_indexes(table):
        if ix.get("name") == index_name:
            return True
    return False


def _try_create_index(name: str, table: str, columns: list[str], **kw: object) -> None:
    bind = op.get_bind()
    if _index_exists(bind, table, name):
        return
    op.create_index(name, table, columns, **kw)


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # --- projects: contracted operational fields (alongside existing stage) ---
    _try_add_column("projects", sa.Column("client_org_id", sa.String(255), nullable=True))
    _try_add_column("projects", sa.Column("state", sa.String(2), nullable=True))
    _try_add_column("projects", sa.Column("project_type", sa.String(50), nullable=True))
    _try_add_column(
        "projects",
        sa.Column("operational_status", sa.String(50), nullable=True),
    )
    _try_add_column("projects", sa.Column("target_in_service_date", sa.Date(), nullable=True))
    _try_add_column("projects", sa.Column("construction_start_date", sa.Date(), nullable=True))
    _try_add_column("projects", sa.Column("budget_total", sa.Numeric(15, 2), nullable=True))
    _try_add_column("projects", sa.Column("created_by", sa.String(), nullable=True))
    _try_create_fk(
        "fk_projects_created_by_users",
        "projects",
        "users",
        ["created_by"],
        ["id"],
    )
    if is_pg:
        op.execute(
            sa.text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'ck_projects_state_tx_in'
                    ) THEN
                        ALTER TABLE projects ADD CONSTRAINT ck_projects_state_tx_in
                        CHECK (state IS NULL OR state IN ('TX', 'IN'));
                    END IF;
                END $$;
                """
            )
        )

    # --- parcels ---
    _try_add_column("segments", sa.Column("planned_start", sa.Date(), nullable=True))
    _try_add_column("segments", sa.Column("planned_finish", sa.Date(), nullable=True))
    _try_add_column("segments", sa.Column("segment_status", sa.String(50), nullable=True))
    op.alter_column("segments", "parcel_id", existing_type=sa.String(), nullable=True)

    _try_add_column("parcels", sa.Column("segment_id", sa.String(), nullable=True))
    _try_create_fk(
        "fk_parcels_segment_id_segments",
        "parcels",
        "segments",
        ["segment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    _try_add_column("parcels", sa.Column("parcel_number", sa.String(100), nullable=True))
    _try_add_column("parcels", sa.Column("county_parcel_id", sa.String(100), nullable=True))
    _try_add_column("parcels", sa.Column("state_pin", sa.String(100), nullable=True))
    _try_add_column("parcels", sa.Column("county", sa.String(100), nullable=True))
    _try_add_column("parcels", sa.Column("parcel_state", sa.String(2), nullable=True))
    _try_add_column("parcels", sa.Column("address", sa.Text(), nullable=True))
    _try_add_column("parcels", sa.Column("legal_description", sa.Text(), nullable=True))
    _try_add_column("parcels", sa.Column("acreage", sa.Numeric(10, 4), nullable=True))
    _try_add_column("parcels", sa.Column("acquisition_type", sa.String(50), nullable=True))
    _try_add_column("parcels", sa.Column("parcel_acquisition_status", sa.String(50), nullable=True))
    _try_add_column("parcels", sa.Column("priority", sa.Integer(), nullable=True, server_default="999"))
    _try_add_column("parcels", sa.Column("construction_need_by", sa.Date(), nullable=True))

    # --- parties ---
    _try_add_column("parties", sa.Column("owner_type", sa.String(50), nullable=True))
    _try_add_column("parties", sa.Column("full_name", sa.String(255), nullable=True))
    _try_add_column("parties", sa.Column("entity_name", sa.String(255), nullable=True))
    _try_add_column("parties", sa.Column("primary_address", sa.Text(), nullable=True))
    _try_add_column("parties", sa.Column("alternate_address", sa.Text(), nullable=True))
    _try_add_column("parties", sa.Column("party_status", sa.String(50), nullable=True))
    _try_add_column("parties", sa.Column("updated_at", sa.DateTime(), nullable=True))

    # --- parcel_interests ---
    _create_table_if_missing(
        bind,
        "parcel_interests",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("parcel_id", sa.String(), nullable=False),
        sa.Column("party_id", sa.String(), nullable=False),
        sa.Column("interest_type", sa.String(50), nullable=False),
        sa.Column("ownership_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("is_primary_contact", sa.Boolean(), nullable=True, server_default="0"),
        sa.Column("interest_doc_id", sa.String(), nullable=True),
        sa.Column("active_flag", sa.Boolean(), nullable=True, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["parcel_id"], ["parcels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["party_id"], ["parties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    _try_create_index("ix_parcel_interests_parcel_id", "parcel_interests", ["parcel_id"])

    # --- title_documents ---
    _create_table_if_missing(
        bind,
        "title_documents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("parcel_id", sa.String(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("vendor", sa.String(255), nullable=True),
        sa.Column("doc_type", sa.String(100), nullable=False),
        sa.Column("file_ref", sa.String(), nullable=True),
        sa.Column("extracted_summary_json", sa.JSON(), nullable=True),
        sa.Column("reviewed_by", sa.String(), nullable=True),
        sa.Column("review_date", sa.Date(), nullable=True),
        sa.Column("issues_identified", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["parcel_id"], ["parcels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["file_ref"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _try_create_index("ix_title_documents_parcel_id", "title_documents", ["parcel_id"])

    # --- negotiations ---
    _create_table_if_missing(
        bind,
        "negotiations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("parcel_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["parcel_id"], ["parcels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    _try_create_index("ix_negotiations_parcel_id", "negotiations", ["parcel_id"])

    # --- counteroffers ---
    _create_table_if_missing(
        bind,
        "counteroffers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("offer_id", sa.String(), nullable=False),
        sa.Column("parcel_id", sa.String(), nullable=False),
        sa.Column("counteroffer_date", sa.Date(), nullable=False),
        sa.Column("proposed_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("non_monetary_terms", sa.Text(), nullable=True),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="under_review"),
        sa.Column("response_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parcel_id"], ["parcels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    _try_create_index("ix_counteroffers_offer_id", "counteroffers", ["offer_id"])

    # --- offers: negotiation + statutory columns ---
    _try_add_column("offers", sa.Column("negotiation_id", sa.String(), nullable=True))
    _try_create_fk(
        "fk_offers_negotiation_id",
        "offers",
        "negotiations",
        ["negotiation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    _try_add_column("offers", sa.Column("appraisal_id", sa.String(), nullable=True))
    _try_create_fk(
        "fk_offers_appraisal_id",
        "offers",
        "appraisals",
        ["appraisal_id"],
        ["id"],
    )
    _try_add_column("offers", sa.Column("wait_period_days", sa.Integer(), nullable=True))
    _try_add_column("offers", sa.Column("earliest_filing_date", sa.Date(), nullable=True))
    _try_add_column("offers", sa.Column("offer_date", sa.Date(), nullable=True))

    # --- payments ---
    _create_table_if_missing(
        bind,
        "payments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("parcel_id", sa.String(), nullable=False),
        sa.Column("payment_type", sa.String(50), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("requested_at", sa.DateTime(), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("offer_id", sa.String(), nullable=True),
        sa.Column("case_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["parcel_id"], ["parcels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"]),
        sa.ForeignKeyConstraint(["case_id"], ["litigation_cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _try_create_index("ix_payments_parcel_id", "payments", ["parcel_id"])

    # --- alignment_segments ---
    _create_table_if_missing(
        bind,
        "alignment_segments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("alignment_id", sa.String(), nullable=False),
        sa.Column("parcel_id", sa.String(), nullable=False),
        sa.Column("segment_geometry", sa.JSON(), nullable=True),
        sa.Column("segment_length_feet", sa.Numeric(10, 2), nullable=True),
        sa.Column("easement_width_feet", sa.Numeric(8, 2), nullable=True),
        sa.Column("easement_area_sqft", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["alignment_id"], ["alignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parcel_id"], ["parcels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    _try_create_index("ix_alignment_segments_alignment", "alignment_segments", ["alignment_id"])
    _try_create_index("ix_alignment_segments_parcel", "alignment_segments", ["parcel_id"])

    # --- litigation: parcel optional + complaint_parcels ---
    op.alter_column("litigation_cases", "parcel_id", existing_type=sa.String(), nullable=True)
    _try_add_column("litigation_cases", sa.Column("state", sa.String(2), nullable=True))
    _try_add_column("litigation_cases", sa.Column("county", sa.String(100), nullable=True))
    _try_add_column("litigation_cases", sa.Column("case_number", sa.String(100), nullable=True))
    _try_add_column("litigation_cases", sa.Column("filing_date", sa.Date(), nullable=True))
    _try_add_column("litigation_cases", sa.Column("judge_name", sa.String(255), nullable=True))
    _try_add_column("litigation_cases", sa.Column("case_type", sa.String(50), nullable=True))
    _try_add_column("litigation_cases", sa.Column("litigation_stage", sa.String(100), nullable=True))
    _try_add_column("litigation_cases", sa.Column("outside_counsel_firm", sa.String(255), nullable=True))
    _try_add_column("litigation_cases", sa.Column("outside_counsel_attorney", sa.String(255), nullable=True))
    _try_add_column("litigation_cases", sa.Column("opposing_counsel", sa.String(255), nullable=True))
    _try_add_column("litigation_cases", sa.Column("quick_take_requested", sa.Boolean(), nullable=True))
    _try_add_column("litigation_cases", sa.Column("quick_take_granted", sa.Boolean(), nullable=True))
    _try_add_column("litigation_cases", sa.Column("possession_date", sa.Date(), nullable=True))
    _try_add_column("litigation_cases", sa.Column("final_award_amount", sa.Numeric(15, 2), nullable=True))
    _try_add_column("litigation_cases", sa.Column("settlement_date", sa.Date(), nullable=True))
    _try_add_column("litigation_cases", sa.Column("case_closed_date", sa.Date(), nullable=True))

    _create_table_if_missing(
        bind,
        "complaint_parcels",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("complaint_id", sa.String(), nullable=False),
        sa.Column("parcel_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["complaint_id"], ["litigation_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parcel_id"], ["parcels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    _try_create_index("ix_complaint_parcels_complaint", "complaint_parcels", ["complaint_id"])
    _try_create_index("ix_complaint_parcels_parcel", "complaint_parcels", ["parcel_id"])

    # --- TX / IN litigation extensions ---
    _create_table_if_missing(
        bind,
        "tx_special_commissioners",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("complaint_id", sa.String(), nullable=False),
        sa.Column("commissioner_number", sa.Integer(), nullable=False),
        sa.Column("commissioner_name", sa.String(255), nullable=False),
        sa.Column("appointment_date", sa.Date(), nullable=False),
        sa.Column("is_freeholder", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["complaint_id"], ["litigation_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_table_if_missing(
        bind,
        "tx_commissioners_hearings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("complaint_id", sa.String(), nullable=False),
        sa.Column("hearing_date", sa.Date(), nullable=False),
        sa.Column("hearing_location", sa.Text(), nullable=True),
        sa.Column("evidence_presented", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["complaint_id"], ["litigation_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_table_if_missing(
        bind,
        "tx_commissioners_awards",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("complaint_id", sa.String(), nullable=False),
        sa.Column("award_date", sa.Date(), nullable=False),
        sa.Column("award_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("objection_deadline", sa.Date(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["complaint_id"], ["litigation_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_table_if_missing(
        bind,
        "tx_bill_of_rights_deliveries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("parcel_id", sa.String(), nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("delivery_type", sa.String(50), nullable=False),
        sa.Column("delivery_date", sa.Date(), nullable=False),
        sa.Column("service_method", sa.String(100), nullable=False),
        sa.Column("document_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["parcel_id"], ["parcels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["parties.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _try_create_index("ix_tx_bor_parcel", "tx_bill_of_rights_deliveries", ["parcel_id"])

    _create_table_if_missing(
        bind,
        "in_court_appraisers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("complaint_id", sa.String(), nullable=False),
        sa.Column("appraiser_name", sa.String(255), nullable=False),
        sa.Column("appraiser_firm", sa.String(255), nullable=True),
        sa.Column("appointment_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["complaint_id"], ["litigation_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_table_if_missing(
        bind,
        "in_appraisers_reports",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("complaint_id", sa.String(), nullable=False),
        sa.Column("report_filing_date", sa.Date(), nullable=False),
        sa.Column("report_mailing_date", sa.Date(), nullable=False),
        sa.Column("appraised_value", sa.Numeric(15, 2), nullable=False),
        sa.Column("exception_deadline", sa.Date(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["complaint_id"], ["litigation_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_table_if_missing(
        bind,
        "in_exceptions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("appraisers_report_id", sa.String(), nullable=False),
        sa.Column("complaint_id", sa.String(), nullable=False),
        sa.Column("filed_by", sa.String(50), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=False),
        sa.Column("grounds", sa.Text(), nullable=True),
        sa.Column("outcome", sa.String(50), nullable=True),
        sa.Column("trial_scheduled", sa.Boolean(), nullable=True),
        sa.Column("document_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["appraisers_report_id"], ["in_appraisers_reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["complaint_id"], ["litigation_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- deadlines (contract fields) ---
    _try_add_column("deadlines", sa.Column("case_id", sa.String(), nullable=True))
    _try_create_fk(
        "fk_deadlines_case_id",
        "deadlines",
        "litigation_cases",
        ["case_id"],
        ["id"],
        ondelete="CASCADE",
    )
    _try_add_column("deadlines", sa.Column("deadline_type", sa.String(100), nullable=True))
    _try_add_column("deadlines", sa.Column("is_automated", sa.Boolean(), nullable=True))
    _try_add_column("deadlines", sa.Column("calculation_rule", sa.Text(), nullable=True))
    _try_add_column("deadlines", sa.Column("responsible_party_id", sa.String(), nullable=True))
    _try_create_fk(
        "fk_deadlines_responsible_party",
        "deadlines",
        "users",
        ["responsible_party_id"],
        ["id"],
    )
    _try_add_column("deadlines", sa.Column("deadline_status", sa.String(50), nullable=True))
    _try_add_column("deadlines", sa.Column("completion_date", sa.Date(), nullable=True))
    _try_add_column("deadlines", sa.Column("alert_sent", sa.Boolean(), nullable=True))
    _try_add_column("deadlines", sa.Column("notes", sa.Text(), nullable=True))
    _try_add_column("deadlines", sa.Column("due_date", sa.Date(), nullable=True))
    _try_add_column("deadlines", sa.Column("source_kind", sa.String(32), nullable=True))
    _try_add_column("deadlines", sa.Column("citation", sa.Text(), nullable=True))
    _try_add_column("deadlines", sa.Column("inputs_json", sa.JSON(), nullable=True))
    op.alter_column("deadlines", "project_id", existing_type=sa.String(), nullable=True)

    # --- documents: contract hash + scope ---
    _try_add_column("documents", sa.Column("complaint_id", sa.String(), nullable=True))
    _try_create_fk(
        "fk_documents_complaint",
        "documents",
        "litigation_cases",
        ["complaint_id"],
        ["id"],
        ondelete="CASCADE",
    )
    _try_add_column("documents", sa.Column("project_id", sa.String(), nullable=True))
    _try_create_fk(
        "fk_documents_project",
        "documents",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    _try_add_column("documents", sa.Column("parcel_id", sa.String(), nullable=True))
    _try_create_fk(
        "fk_documents_parcel",
        "documents",
        "parcels",
        ["parcel_id"],
        ["id"],
        ondelete="CASCADE",
    )
    _try_add_column("documents", sa.Column("document_type", sa.String(100), nullable=True))
    _try_add_column("documents", sa.Column("document_name", sa.String(255), nullable=True))
    _try_add_column("documents", sa.Column("file_name", sa.String(255), nullable=True))
    _try_add_column("documents", sa.Column("file_path", sa.String(), nullable=True))
    _try_add_column("documents", sa.Column("file_size", sa.BigInteger(), nullable=True))
    _try_add_column("documents", sa.Column("mime_type", sa.String(100), nullable=True))
    _try_add_column("documents", sa.Column("document_date", sa.Date(), nullable=True))
    _try_add_column("documents", sa.Column("is_current_version", sa.Boolean(), nullable=True))
    _try_add_column("documents", sa.Column("tags", sa.JSON(), nullable=True))
    _try_add_column("documents", sa.Column("is_confidential", sa.Boolean(), nullable=True))
    _try_add_column("documents", sa.Column("content_hash", sa.String(64), nullable=True))
    _try_add_column("documents", sa.Column("updated_at", sa.DateTime(), nullable=True))

    # --- notices / service_attempts (additive string columns for contract enums) ---
    _try_add_column("notices", sa.Column("owner_party_id", sa.String(), nullable=True))
    _try_create_fk(
        "fk_notices_owner_party",
        "notices",
        "parties",
        ["owner_party_id"],
        ["id"],
    )
    _try_add_column("notices", sa.Column("notice_state", sa.String(2), nullable=True))
    _try_add_column("notices", sa.Column("notice_date", sa.Date(), nullable=True))
    _try_add_column("notices", sa.Column("service_required", sa.Boolean(), nullable=True))
    _try_add_column("notices", sa.Column("service_deadline", sa.Date(), nullable=True))
    _try_add_column("notices", sa.Column("response_deadline", sa.Date(), nullable=True))
    _try_add_column("notices", sa.Column("notice_type_code", sa.String(100), nullable=True))
    _try_add_column("notices", sa.Column("notice_status_code", sa.String(50), nullable=True))

    _try_add_column("service_attempts", sa.Column("service_method_code", sa.String(100), nullable=True))
    _try_add_column("service_attempts", sa.Column("service_address", sa.Text(), nullable=True))
    _try_add_column("service_attempts", sa.Column("tracking_number", sa.String(100), nullable=True))
    _try_add_column("service_attempts", sa.Column("delivery_date", sa.Date(), nullable=True))
    _try_add_column("service_attempts", sa.Column("delivery_signature", sa.String(255), nullable=True))
    _try_add_column("service_attempts", sa.Column("outcome_code", sa.String(50), nullable=True))
    _try_add_column("service_attempts", sa.Column("process_server_name", sa.String(255), nullable=True))
    _try_add_column("service_attempts", sa.Column("affidavit_document_id", sa.String(), nullable=True))
    _try_add_column("service_attempts", sa.Column("publication_newspaper", sa.String(255), nullable=True))
    _try_add_column("service_attempts", sa.Column("publication_dates", sa.JSON(), nullable=True))

    # --- communications ---
    _try_add_column("communications", sa.Column("owner_party_id", sa.String(), nullable=True))
    _try_create_fk(
        "fk_comms_owner_party",
        "communications",
        "parties",
        ["owner_party_id"],
        ["id"],
    )
    _try_add_column("communications", sa.Column("communication_type", sa.String(100), nullable=True))
    _try_add_column("communications", sa.Column("communication_date", sa.DateTime(), nullable=True))
    _try_add_column("communications", sa.Column("initiated_by", sa.String(), nullable=True))
    _try_create_fk(
        "fk_comms_initiated_by",
        "communications",
        "users",
        ["initiated_by"],
        ["id"],
    )
    _try_add_column("communications", sa.Column("subject", sa.String(255), nullable=True))
    _try_add_column("communications", sa.Column("summary", sa.Text(), nullable=True))
    _try_add_column("communications", sa.Column("related_to", sa.String(100), nullable=True))
    _try_add_column("communications", sa.Column("attachments", sa.JSON(), nullable=True))
    _try_add_column("communications", sa.Column("follow_up_required", sa.Boolean(), nullable=True))
    _try_add_column("communications", sa.Column("follow_up_date", sa.Date(), nullable=True))
    _try_add_column("communications", sa.Column("follow_up_assigned_to", sa.String(), nullable=True))
    _try_create_fk(
        "fk_comms_follow_up",
        "communications",
        "users",
        ["follow_up_assigned_to"],
        ["id"],
    )

    # --- templates (contract) ---
    _try_add_column("templates", sa.Column("template_type", sa.String(100), nullable=True))
    _try_add_column("templates", sa.Column("state", sa.String(2), nullable=True))
    _try_add_column("templates", sa.Column("template_name", sa.String(255), nullable=True))
    _try_add_column("templates", sa.Column("template_content", sa.Text(), nullable=True))
    _try_add_column("templates", sa.Column("variables", sa.JSON(), nullable=True))
    _try_add_column("templates", sa.Column("schema_json", sa.JSON(), nullable=True))
    _try_add_column("templates", sa.Column("version_int", sa.Integer(), nullable=True))
    _try_add_column("templates", sa.Column("template_status", sa.String(50), nullable=True))
    _try_add_column("templates", sa.Column("approved_by", sa.String(), nullable=True))
    _try_create_fk(
        "fk_templates_approved_by",
        "templates",
        "users",
        ["approved_by"],
        ["id"],
    )
    _try_add_column("templates", sa.Column("approved_date", sa.Date(), nullable=True))
    _try_add_column("templates", sa.Column("created_by", sa.String(), nullable=True))
    _try_create_fk(
        "fk_templates_created_by",
        "templates",
        "users",
        ["created_by"],
        ["id"],
    )
    _try_add_column("templates", sa.Column("updated_at", sa.DateTime(), nullable=True))

    # --- appraisals (contract columns) ---
    _try_add_column("appraisals", sa.Column("appraisal_type", sa.String(50), nullable=True))
    _try_add_column("appraisals", sa.Column("appraiser_name", sa.String(255), nullable=True))
    _try_add_column("appraisals", sa.Column("appraisal_date", sa.Date(), nullable=True))
    _try_add_column("appraisals", sa.Column("appraised_value", sa.Numeric(15, 2), nullable=True))
    _try_add_column("appraisals", sa.Column("permanent_easement_value", sa.Numeric(15, 2), nullable=True))
    _try_add_column("appraisals", sa.Column("temporary_easement_value", sa.Numeric(15, 2), nullable=True))
    _try_add_column("appraisals", sa.Column("severance_damages", sa.Numeric(15, 2), nullable=True))
    _try_add_column("appraisals", sa.Column("document_id", sa.String(), nullable=True))
    _try_create_fk(
        "fk_appraisals_document",
        "appraisals",
        "documents",
        ["document_id"],
        ["id"],
    )
    _try_add_column("appraisals", sa.Column("is_current", sa.Boolean(), nullable=True))
    _try_add_column("appraisals", sa.Column("staleness_flag", sa.Boolean(), nullable=True))
    _try_add_column("appraisals", sa.Column("updated_at", sa.DateTime(), nullable=True))

    # --- curative_items ---
    _try_add_column("curative_items", sa.Column("issue_type", sa.String(100), nullable=True))
    _try_add_column("curative_items", sa.Column("is_blocking", sa.Boolean(), nullable=True))
    _try_add_column("curative_items", sa.Column("assigned_to", sa.String(), nullable=True))
    _try_create_fk(
        "fk_curative_assigned_to",
        "curative_items",
        "users",
        ["assigned_to"],
        ["id"],
    )
    _try_add_column("curative_items", sa.Column("resolution_date", sa.Date(), nullable=True))
    _try_add_column("curative_items", sa.Column("resolution_method", sa.Text(), nullable=True))
    _try_add_column("curative_items", sa.Column("cost", sa.Numeric(15, 2), nullable=True))
    _try_add_column("curative_items", sa.Column("notes", sa.Text(), nullable=True))
    _try_add_column(
        "curative_items",
        sa.Column("title_document_id", sa.String(), nullable=True),
    )
    _try_create_fk(
        "fk_curative_title_document",
        "curative_items",
        "title_documents",
        ["title_document_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # --- managed objection types (lookup) ---
    _create_table_if_missing(
        bind,
        "litigation_objection_types",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=True, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    _create_table_if_missing(
        bind,
        "litigation_objections",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("complaint_id", sa.String(), nullable=False),
        sa.Column("objection_type_id", sa.String(), nullable=True),
        sa.Column("filed", sa.Boolean(), nullable=True),
        sa.Column("date_filed", sa.Date(), nullable=True),
        sa.Column("outcome", sa.String(50), nullable=True),
        sa.Column("discovery_deadline", sa.Date(), nullable=True),
        sa.Column("hearing_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["complaint_id"], ["litigation_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["objection_type_id"], ["litigation_objection_types.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _try_create_index("ix_litigation_objections_complaint", "litigation_objections", ["complaint_id"])

    # --- audit digest anchor (tamper-evidence) ---
    _create_table_if_missing(
        bind,
        "audit_digest_anchors",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("firm_id", sa.String(), nullable=True),
        sa.Column("digest_date", sa.Date(), nullable=False),
        sa.Column("chain_tip_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_digest_anchors")
    op.drop_index("ix_litigation_objections_complaint", table_name="litigation_objections")
    op.drop_table("litigation_objections")
    op.drop_table("litigation_objection_types")

    op.drop_constraint("fk_curative_title_document", "curative_items", type_="foreignkey")
    op.drop_column("curative_items", "title_document_id")
    op.drop_constraint("fk_curative_assigned_to", "curative_items", type_="foreignkey")
    for col in (
        "notes",
        "cost",
        "resolution_method",
        "resolution_date",
        "assigned_to",
        "is_blocking",
        "issue_type",
    ):
        op.drop_column("curative_items", col)

    op.drop_constraint("fk_appraisals_document", "appraisals", type_="foreignkey")
    for col in (
        "updated_at",
        "staleness_flag",
        "is_current",
        "document_id",
        "severance_damages",
        "temporary_easement_value",
        "permanent_easement_value",
        "appraised_value",
        "appraisal_date",
        "appraiser_name",
        "appraisal_type",
    ):
        op.drop_column("appraisals", col)

    op.drop_constraint("fk_templates_created_by", "templates", type_="foreignkey")
    op.drop_constraint("fk_templates_approved_by", "templates", type_="foreignkey")
    for col in (
        "updated_at",
        "created_by",
        "approved_date",
        "approved_by",
        "template_status",
        "version_int",
        "schema_json",
        "variables",
        "template_content",
        "template_name",
        "state",
        "template_type",
    ):
        op.drop_column("templates", col)

    op.drop_constraint("fk_comms_follow_up", "communications", type_="foreignkey")
    op.drop_constraint("fk_comms_initiated_by", "communications", type_="foreignkey")
    op.drop_constraint("fk_comms_owner_party", "communications", type_="foreignkey")
    for col in (
        "follow_up_assigned_to",
        "follow_up_date",
        "follow_up_required",
        "attachments",
        "related_to",
        "summary",
        "subject",
        "initiated_by",
        "communication_date",
        "communication_type",
        "owner_party_id",
    ):
        op.drop_column("communications", col)

    for col in (
        "publication_dates",
        "publication_newspaper",
        "affidavit_document_id",
        "process_server_name",
        "outcome_code",
        "delivery_signature",
        "delivery_date",
        "tracking_number",
        "service_address",
        "service_method_code",
    ):
        op.drop_column("service_attempts", col)

    for col in (
        "notice_status_code",
        "notice_type_code",
        "response_deadline",
        "service_deadline",
        "service_required",
        "notice_date",
        "notice_state",
        "owner_party_id",
    ):
        op.drop_column("notices", col)

    op.drop_constraint("fk_documents_parcel", "documents", type_="foreignkey")
    op.drop_constraint("fk_documents_project", "documents", type_="foreignkey")
    op.drop_constraint("fk_documents_complaint", "documents", type_="foreignkey")
    for col in (
        "updated_at",
        "content_hash",
        "is_confidential",
        "tags",
        "is_current_version",
        "document_date",
        "mime_type",
        "file_size",
        "file_path",
        "file_name",
        "document_name",
        "document_type",
        "parcel_id",
        "project_id",
        "complaint_id",
    ):
        op.drop_column("documents", col)

    op.drop_constraint("fk_deadlines_responsible_party", "deadlines", type_="foreignkey")
    op.drop_constraint("fk_deadlines_case_id", "deadlines", type_="foreignkey")
    for col in (
        "inputs_json",
        "citation",
        "source_kind",
        "due_date",
        "notes",
        "alert_sent",
        "completion_date",
        "deadline_status",
        "responsible_party_id",
        "calculation_rule",
        "is_automated",
        "deadline_type",
        "case_id",
    ):
        op.drop_column("deadlines", col)
    op.alter_column("deadlines", "project_id", existing_type=sa.String(), nullable=False)

    op.drop_table("in_exceptions")
    op.drop_table("in_appraisers_reports")
    op.drop_table("in_court_appraisers")
    op.drop_table("tx_bill_of_rights_deliveries")
    op.drop_table("tx_commissioners_awards")
    op.drop_table("tx_commissioners_hearings")
    op.drop_table("tx_special_commissioners")

    op.drop_index("ix_complaint_parcels_parcel", table_name="complaint_parcels")
    op.drop_index("ix_complaint_parcels_complaint", table_name="complaint_parcels")
    op.drop_table("complaint_parcels")

    for col in (
        "case_closed_date",
        "settlement_date",
        "final_award_amount",
        "possession_date",
        "quick_take_granted",
        "quick_take_requested",
        "opposing_counsel",
        "outside_counsel_attorney",
        "outside_counsel_firm",
        "litigation_stage",
        "case_type",
        "judge_name",
        "filing_date",
        "case_number",
        "county",
        "state",
    ):
        op.drop_column("litigation_cases", col)
    op.alter_column("litigation_cases", "parcel_id", existing_type=sa.String(), nullable=False)

    op.drop_index("ix_alignment_segments_parcel", table_name="alignment_segments")
    op.drop_index("ix_alignment_segments_alignment", table_name="alignment_segments")
    op.drop_table("alignment_segments")

    op.drop_index("ix_payments_parcel_id", table_name="payments")
    op.drop_table("payments")

    op.drop_constraint("fk_offers_appraisal_id", "offers", type_="foreignkey")
    op.drop_constraint("fk_offers_negotiation_id", "offers", type_="foreignkey")
    for col in ("offer_date", "earliest_filing_date", "wait_period_days", "appraisal_id", "negotiation_id"):
        op.drop_column("offers", col)

    op.drop_index("ix_counteroffers_offer_id", table_name="counteroffers")
    op.drop_table("counteroffers")

    op.drop_index("ix_negotiations_parcel_id", table_name="negotiations")
    op.drop_table("negotiations")

    op.drop_index("ix_title_documents_parcel_id", table_name="title_documents")
    op.drop_table("title_documents")

    op.drop_index("ix_parcel_interests_parcel_id", table_name="parcel_interests")
    op.drop_table("parcel_interests")

    for col in ("updated_at", "party_status", "alternate_address", "primary_address", "entity_name", "full_name", "owner_type"):
        op.drop_column("parties", col)

    op.drop_constraint("fk_parcels_segment_id_segments", "parcels", type_="foreignkey")
    for col in (
        "construction_need_by",
        "priority",
        "parcel_acquisition_status",
        "acquisition_type",
        "acreage",
        "legal_description",
        "address",
        "parcel_state",
        "county",
        "state_pin",
        "county_parcel_id",
        "parcel_number",
        "segment_id",
    ):
        op.drop_column("parcels", col)

    op.drop_column("segments", "segment_status")
    op.drop_column("segments", "planned_finish")
    op.drop_column("segments", "planned_start")
    op.alter_column("segments", "parcel_id", existing_type=sa.String(), nullable=False)

    op.drop_constraint("fk_projects_created_by_users", "projects", type_="foreignkey")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE projects DROP CONSTRAINT IF EXISTS ck_projects_state_tx_in")
    for col in (
        "created_by",
        "budget_total",
        "construction_start_date",
        "target_in_service_date",
        "operational_status",
        "project_type",
        "state",
        "client_org_id",
    ):
        op.drop_column("projects", col)
