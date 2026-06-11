import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text

from app.api.routes import (
    auth as auth_routes,
    cases,
    jurisdictions,
    projects,
    templates,
    ai,
    health,
    workflows,
    integrations,
    portal,
    communications,
    notices,
    packet,
    budgets,
    binder,
    notifications,
    parcels,
    deadlines,
    title,
    appraisals,
    ops,
    outside,
    agents,
    roe,
    offers,
    alignments,
    litigation,
    esign,
    chat,
    admin,
    # AI-First modules
    rules_ops,
    audit_ai,
    approvals_api,
    qa,
    rag,
    copilot,
    analytics,
    websocket,
    predictions,
    tasks,
)
from app.core.config import get_settings
from app.db.session import Base, SessionLocal, engine
from app.db import models
from app.telemetry import configure_tracing, instrument_app
from app.security.auth_middleware import AuthEnforcementMiddleware
from app.security.mutation_audit_middleware import MutationAuditMiddleware

logger = logging.getLogger(__name__)

settings = get_settings()
configure_tracing()

# Fail fast if prod config still carries dev placeholders (Phase 3.3).
_prod_problems = settings.validate_prod_secrets()
if _prod_problems:
    raise RuntimeError(
        "Refusing to start with insecure configuration: " + "; ".join(_prod_problems)
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment != "dev" or settings.database_required:
        _run_migrations_if_enabled()
        _assert_database_ready()
    else:
        _bootstrap_dev_db()
    yield


app = FastAPI(
    title="LandGrant API",
    version="0.1.0",
    docs_url="/docs" if settings.environment == "dev" else None,
    redoc_url=None,
    lifespan=lifespan,
)

# --- Rate limiting (Phase 3.3) -------------------------------------------------
# We attach slowapi lazily so test environments without the dependency still
# import cleanly.  Each request is keyed on client IP + authenticated subject.
if settings.rate_limit_enabled:
    try:
        from slowapi import Limiter
        from slowapi.errors import RateLimitExceeded
        from slowapi.middleware import SlowAPIMiddleware
        from slowapi.util import get_remote_address

        def _rate_key(request: Request) -> str:
            principal = getattr(request.state, "principal", None)
            who = principal.user_id if principal is not None else "anon"
            return f"{get_remote_address(request)}::{who}"

        limiter = Limiter(
            key_func=_rate_key,
            default_limits=[settings.rate_limit_default],
        )
        app.state.limiter = limiter

        async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
            return Response(
                content='{"detail":"Too Many Requests"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "1"},
            )

        app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
        app.add_middleware(SlowAPIMiddleware)
    except ModuleNotFoundError as exc:
        # ``slowapi`` is optional during testing so the test container doesn't
        # need the extra dep. Log once so ops can tell when the limiter is off.
        import logging

        _log = logging.getLogger(__name__)
        if settings.environment == "dev":
            _log.warning("Rate limiter disabled - slowapi not installed: %s", exc)
        else:
            # Production/staging must never silently ship without rate limits.
            raise RuntimeError(
                "rate_limit_enabled=True but slowapi is not installed; "
                "install slowapi or set RATE_LIMIT_ENABLED=false"
            ) from exc
    except Exception as exc:
        # Any other failure is a configuration bug we want to surface loudly
        # in non-dev environments instead of booting without protection.
        import logging

        logging.getLogger(__name__).exception(
            "Rate limiter initialisation failed: %s", exc
        )
        if settings.environment != "dev":
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(self)"
        )
        if settings.environment != "dev":
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains"
            )
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuthEnforcementMiddleware)
app.add_middleware(MutationAuditMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Persona"],
    allow_credentials=True,
)

app.include_router(auth_routes.router)
app.include_router(health.router)
app.include_router(jurisdictions.router)
app.include_router(cases.router)
app.include_router(projects.router)
app.include_router(templates.router)
app.include_router(ai.router)
app.include_router(workflows.router)
app.include_router(integrations.router)
app.include_router(portal.router)
app.include_router(communications.router)
app.include_router(notices.router)
app.include_router(packet.router)
app.include_router(budgets.router)
app.include_router(binder.router)
app.include_router(notifications.router)
app.include_router(parcels.router)
app.include_router(deadlines.router)
app.include_router(title.router)
app.include_router(appraisals.router)
app.include_router(ops.router)
app.include_router(outside.router)
app.include_router(agents.router)
app.include_router(roe.router)
app.include_router(offers.router)
app.include_router(alignments.router)
app.include_router(litigation.router)
app.include_router(esign.router)
app.include_router(chat.router)
app.include_router(admin.router)

# AI-First modules
app.include_router(rules_ops.router)
app.include_router(audit_ai.router)
app.include_router(approvals_api.router)
app.include_router(qa.router)
app.include_router(rag.router)
app.include_router(copilot.router)
app.include_router(analytics.router)

# Real-time WebSocket
app.include_router(websocket.router)

# ML Predictions
app.include_router(predictions.router)

# Task Management
app.include_router(tasks.router)

# Attach OpenTelemetry auto-instrumentation now that routes are mounted.
instrument_app(app)


def _assert_database_ready() -> None:
    """Fail startup/readiness when the system of record is unreachable."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def _run_migrations_if_enabled() -> None:
    if not settings.alembic_auto:
        return

    from alembic import command
    from alembic.config import Config

    import os

    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option(
        "sqlalchemy.url", settings.effective_database_url.replace("%", "%%")
    )
    command.upgrade(cfg, "head")


def _seed_library_templates(db) -> None:
    """Idempotent: load ``templates/library/*/meta.json`` into ``templates`` rows."""
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "templates" / "library"
    if not root.is_dir():
        return
    for meta_path in sorted(root.glob("**/meta.json")):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        tid = meta.get("id")
        if not tid or db.get(models.Template, tid):
            continue
        folder = meta_path.parent
        tmpl_path = folder / "template.md"
        content = ""
        if tmpl_path.is_file():
            try:
                content = tmpl_path.read_text(encoding="utf-8")
            except OSError:
                content = ""
        ver = str(meta.get("version") or "1.0.0")
        jur = (meta.get("jurisdiction") or "").strip().upper() or None
        state = jur[:2] if jur and len(jur) >= 2 else None
        variables = meta.get("variables") or {}
        db.add(
            models.Template(
                id=tid,
                version=ver,
                locale=str(meta.get("locale") or "en-US"),
                jurisdiction=jur,
                variables_schema=variables,
                redactions=meta.get("redactions") or [],
                privilege=str(meta.get("privilege") or "non_privileged"),
                classifications=meta.get("classifications") or [],
                template_type=str(meta.get("template_type") or "letter"),
                state=state,
                template_name=str(
                    meta.get("template_name") or tid.replace("_", " ").title()
                ),
                template_content=content or None,
                variables=variables,
                schema_json=meta,
                version_int=1,
                template_status="approved",
            )
        )


def _bootstrap_dev_db() -> None:
    """Local-dev convenience: create tables and seed demo data.

    In production (or when ``ALEMBIC_AUTO=1`` is set) we defer schema creation
    to ``alembic upgrade head`` so migrations stay authoritative.  The dev
    fallback uses ``Base.metadata.create_all`` only when Alembic has not been
    opted into yet.
    """
    if settings.environment != "dev":
        return

    try:
        if settings.alembic_auto:
            _run_migrations_if_enabled()
        else:
            Base.metadata.create_all(bind=engine)
    except Exception:
        return

    # Seed the prompt registry so /audit/ai-events has valid template IDs even
    # on a fresh dev database.  This is idempotent.
    db = SessionLocal()
    try:
        from app.services.prompt_registry import seed_default_prompts
        from app.security.tenancy import backfill_firm_ids

        try:
            seed_default_prompts(db)
        except Exception:
            db.rollback()

        try:
            backfill_firm_ids(db)
        except Exception:
            db.rollback()
    finally:
        db.close()

    db = SessionLocal()
    try:
        try:
            from datetime import datetime, timedelta
            import uuid

            project1_id = f"PRJ-{1:03d}"
            project2_id = f"PRJ-{2:03d}"
            parcel1_id = f"PARCEL-{1:03d}"
            parcel2_id = f"PARCEL-{2:03d}"
            parcel3_id = f"PARCEL-{3:03d}"
            parcel4_id = f"PARCEL-{4:03d}"
            parcel5_id = f"PARCEL-{5:03d}"

            if db.get(models.Project, project1_id):
                return

            # === Default firm (FK target for users / parcel grants) ===
            # In dev we create tables via ``create_all`` and skip Alembic, so the
            # default firm seeded by migration 0003 is absent. Insert it (and
            # flush) before any ``firm_id``-bearing rows or the whole seed
            # transaction rolls back on an FK violation.
            if not db.get(models.Firm, models.DEFAULT_FIRM_ID):
                db.add(
                    models.Firm(
                        id=models.DEFAULT_FIRM_ID,
                        name="Default Firm",
                        slug=models.DEFAULT_FIRM_ID,
                        active=True,
                    )
                )
                db.flush()

            # === Projects ===
            project1 = models.Project(
                id=project1_id,
                firm_id=models.DEFAULT_FIRM_ID,
                name="Utility Corridor Expansion",
                jurisdiction_code="TX",
                state="TX",
                project_type="pipeline",
                operational_status="active",
                stage=models.ProjectStage.NEGOTIATION,
                risk_score=35,
                next_deadline_at=datetime.utcnow() + timedelta(days=12),
            )
            project2 = models.Project(
                id=project2_id,
                firm_id=models.DEFAULT_FIRM_ID,
                name="Highway 281 Widening",
                jurisdiction_code="TX",
                state="TX",
                project_type="other",
                operational_status="planning",
                stage=models.ProjectStage.INTAKE,
                risk_score=20,
                next_deadline_at=datetime.utcnow() + timedelta(days=30),
            )
            db.add(project1)
            db.add(project2)

            # === Parcels (5 total with varied risk/deadline) ===
            parcel1 = models.Parcel(
                id=parcel1_id,
                project_id=project1.id,
                county_fips="48439",
                parcel_number="P-001",
                county="Montgomery County",
                parcel_state="TX",
                acquisition_type="permanent_easement",
                stage="negotiation",
                risk_score=40,
                next_deadline_at=datetime.utcnow() + timedelta(days=7),
            )
            parcel2 = models.Parcel(
                id=parcel2_id,
                project_id=project1.id,
                county_fips="48439",
                parcel_number="P-002",
                county="Montgomery County",
                parcel_state="TX",
                acquisition_type="fee_simple",
                stage="intake",
                risk_score=75,
                next_deadline_at=datetime.utcnow() + timedelta(days=3),
            )
            parcel3 = models.Parcel(
                id=parcel3_id,
                project_id=project1.id,
                county_fips="48439",
                parcel_number="P-003",
                county="Montgomery County",
                parcel_state="TX",
                acquisition_type="temporary_easement",
                stage="offer_sent",
                risk_score=25,
                next_deadline_at=datetime.utcnow() + timedelta(days=14),
            )
            parcel4 = models.Parcel(
                id=parcel4_id,
                project_id=project1.id,
                county_fips="48453",
                parcel_number="P-004",
                county="Travis County",
                parcel_state="TX",
                acquisition_type="fee_simple",
                stage="closed",
                risk_score=10,
                next_deadline_at=None,
            )
            parcel5 = models.Parcel(
                id=parcel5_id,
                project_id=project2.id,
                county_fips="48029",
                parcel_number="P-005",
                county="Bexar County",
                parcel_state="TX",
                acquisition_type="permanent_easement",
                stage="intake",
                risk_score=55,
                next_deadline_at=datetime.utcnow() + timedelta(days=21),
            )
            db.add(parcel1)
            db.add(parcel2)
            db.add(parcel3)
            db.add(parcel4)
            db.add(parcel5)
            # Flush projects + parcels first so downstream seed rows (appraisals,
            # communications, AI decisions, etc.) see the FK targets. Without
            # this explicit boundary SQLAlchemy occasionally ordered inserts in
            # a way that violated foreign keys on Postgres, which caused the
            # whole seed transaction to silently roll back and left the demo
            # dataset empty.
            db.flush()

            # === Parties ===
            owner1 = models.Party(
                id="OWNER-001",
                name="Riverbend Farms LLC",
                role="owner",
                email="owner@example.com",
            )
            owner2 = models.Party(
                id="OWNER-002",
                name="Johnson Family Trust",
                role="owner",
                email="johnson@example.com",
            )
            owner3 = models.Party(
                id="OWNER-003",
                name="Westside Holdings Inc",
                role="owner",
                email="westside@example.com",
            )
            db.add(owner1)
            db.add(owner2)
            db.add(owner3)

            # === Parcel-Party relationships ===
            db.add(
                models.ParcelParty(
                    parcel_id=parcel1_id,
                    party_id="OWNER-001",
                    relationship_type="owner",
                )
            )
            db.add(
                models.ParcelParty(
                    parcel_id=parcel2_id,
                    party_id="OWNER-002",
                    relationship_type="owner",
                )
            )
            db.add(
                models.ParcelParty(
                    parcel_id=parcel3_id,
                    party_id="OWNER-002",
                    relationship_type="owner",
                )
            )
            db.add(
                models.ParcelParty(
                    parcel_id=parcel4_id,
                    party_id="OWNER-003",
                    relationship_type="owner",
                )
            )
            db.add(
                models.ParcelParty(
                    parcel_id=parcel5_id,
                    party_id="OWNER-003",
                    relationship_type="owner",
                )
            )

            # === Parcel interests (contracted junction) ===
            db.add(
                models.ParcelInterest(
                    id="PI-001",
                    parcel_id=parcel1_id,
                    party_id="OWNER-001",
                    interest_type="fee_owner",
                    is_primary_contact=True,
                    active_flag=True,
                )
            )
            db.add(
                models.ParcelInterest(
                    id="PI-002",
                    parcel_id=parcel2_id,
                    party_id="OWNER-002",
                    interest_type="fee_owner",
                    is_primary_contact=True,
                    active_flag=True,
                )
            )
            db.add(
                models.ParcelInterest(
                    id="PI-003",
                    parcel_id=parcel3_id,
                    party_id="OWNER-002",
                    interest_type="fee_owner",
                    is_primary_contact=True,
                    active_flag=True,
                )
            )
            db.add(
                models.ParcelInterest(
                    id="PI-004",
                    parcel_id=parcel4_id,
                    party_id="OWNER-003",
                    interest_type="fee_owner",
                    is_primary_contact=True,
                    active_flag=True,
                )
            )
            db.add(
                models.ParcelInterest(
                    id="PI-005",
                    parcel_id=parcel5_id,
                    party_id="OWNER-003",
                    interest_type="fee_owner",
                    is_primary_contact=True,
                    active_flag=True,
                )
            )

            # === Communications (multiple channels) ===
            db.add(
                models.Communication(
                    id=str(uuid.uuid4()),
                    parcel_id=parcel1_id,
                    project_id=project1.id,
                    channel="email",
                    direction="outbound",
                    content="Final offer delivered",
                    delivery_status="delivered",
                    delivery_proof={"provider": "SendGrid", "id": "sg_demo_001"},
                    sla_due_at=datetime.utcnow() + timedelta(days=3),
                    hash="hash-demo-001",
                )
            )
            db.add(
                models.Communication(
                    id=str(uuid.uuid4()),
                    parcel_id=parcel1_id,
                    project_id=project1.id,
                    channel="sms",
                    direction="outbound",
                    content="Reminder: Please review the offer documents",
                    delivery_status="delivered",
                    delivery_proof={"provider": "Twilio", "id": "SM_demo_001"},
                    sla_due_at=datetime.utcnow() + timedelta(days=1),
                    hash="hash-demo-002",
                )
            )
            db.add(
                models.Communication(
                    id=str(uuid.uuid4()),
                    parcel_id=parcel1_id,
                    project_id=project1.id,
                    channel="certified_mail",
                    direction="outbound",
                    content="Formal offer packet delivered via certified mail",
                    delivery_status="delivered",
                    delivery_proof={
                        "provider": "Lob",
                        "tracking": "9400111899223456789012",
                    },
                    sla_due_at=datetime.utcnow() + timedelta(days=5),
                    hash="hash-demo-003",
                )
            )
            db.add(
                models.Communication(
                    id=str(uuid.uuid4()),
                    parcel_id=parcel2_id,
                    project_id=project1.id,
                    channel="email",
                    direction="outbound",
                    content="Initial contact letter sent",
                    delivery_status="pending",
                    delivery_proof={"provider": "SendGrid", "id": "sg_demo_002"},
                    sla_due_at=datetime.utcnow() + timedelta(days=2),
                    hash="hash-demo-004",
                )
            )

            # === Rule Results ===
            db.add(
                models.RuleResult(
                    id=str(uuid.uuid4()),
                    parcel_id=parcel1_id,
                    project_id=project1.id,
                    rule_id="valuation_threshold",
                    version="1.0.0",
                    citation="Tex. Prop. Code §21.0113",
                    payload={"parcel.assessed_value": 300000},
                )
            )
            db.add(
                models.RuleResult(
                    id=str(uuid.uuid4()),
                    parcel_id=parcel1_id,
                    project_id=project1.id,
                    rule_id="good_faith_meeting",
                    version="1.0.0",
                    citation="Tex. Prop. Code §21.0114",
                    payload={"meeting_scheduled": True, "meeting_date": "2026-01-15"},
                )
            )
            db.add(
                models.RuleResult(
                    id=str(uuid.uuid4()),
                    parcel_id=parcel2_id,
                    project_id=project1.id,
                    rule_id="valuation_threshold",
                    version="1.0.0",
                    citation="Tex. Prop. Code §21.0113",
                    payload={"parcel.assessed_value": 450000},
                )
            )

            # === Budget ===
            db.add(
                models.Budget(
                    id=str(uuid.uuid4()),
                    project_id=project1.id,
                    cap_amount=250000,
                    actual_amount=175000,
                    variance=-75000,
                )
            )
            db.add(
                models.Budget(
                    id=str(uuid.uuid4()),
                    project_id=project2.id,
                    cap_amount=500000,
                    actual_amount=50000,
                    variance=-450000,
                )
            )

            # === Documents (for title instruments) ===
            doc1_id = str(uuid.uuid4())
            doc2_id = str(uuid.uuid4())
            db.add(
                models.Document(
                    id=doc1_id,
                    doc_type="title_instrument",
                    version="1.0.0",
                    sha256="abc123def456",
                    storage_path=f"local_storage/title/{parcel1_id}/deed.pdf",
                    metadata_json={
                        "filename": "deed.pdf",
                        "content_type": "application/pdf",
                    },
                )
            )
            db.add(
                models.Document(
                    id=doc2_id,
                    doc_type="title_instrument",
                    version="1.0.0",
                    sha256="xyz789abc123",
                    storage_path=f"local_storage/title/{parcel1_id}/survey.pdf",
                    metadata_json={
                        "filename": "survey.pdf",
                        "content_type": "application/pdf",
                    },
                )
            )

            # === Title Instruments ===
            db.add(
                models.TitleInstrument(
                    id=str(uuid.uuid4()),
                    parcel_id=parcel1_id,
                    document_id=doc1_id,
                    ocr_payload={
                        "confidence": 0.92,
                        "entities": ["grantor", "grantee", "legal_description"],
                        "source": "azure_form_recognizer",
                    },
                    metadata_json={
                        "instrument_type": "warranty_deed",
                        "recorded_date": "2020-03-15",
                    },
                    created_at=datetime.utcnow(),
                )
            )
            db.add(
                models.TitleInstrument(
                    id=str(uuid.uuid4()),
                    parcel_id=parcel1_id,
                    document_id=doc2_id,
                    ocr_payload={
                        "confidence": 0.88,
                        "entities": ["surveyor", "boundaries"],
                        "source": "azure_form_recognizer",
                    },
                    metadata_json={
                        "instrument_type": "survey",
                        "survey_date": "2019-11-20",
                    },
                    created_at=datetime.utcnow(),
                )
            )

            # === Appraisals ===
            db.add(
                models.Appraisal(
                    id=str(uuid.uuid4()),
                    parcel_id=parcel1_id,
                    value=350000,
                    summary="Commercial property with highway frontage. Appraised using sales comparison approach with 3 comparable sales in the area.",
                    comps=[
                        {
                            "address": "123 Highway Dr",
                            "sale_price": 340000,
                            "sale_date": "2025-06-15",
                        },
                        {
                            "address": "456 Commerce Blvd",
                            "sale_price": 365000,
                            "sale_date": "2025-08-22",
                        },
                        {
                            "address": "789 Industrial Way",
                            "sale_price": 345000,
                            "sale_date": "2025-09-10",
                        },
                    ],
                    completed_at=datetime.utcnow() - timedelta(days=5),
                )
            )

            # === Deadlines ===
            db.add(
                models.Deadline(
                    id=str(uuid.uuid4()),
                    project_id=project1.id,
                    parcel_id=parcel1_id,
                    title="Final offer response due",
                    due_at=datetime.utcnow() + timedelta(days=7),
                    timezone="America/Chicago",
                )
            )
            db.add(
                models.Deadline(
                    id=str(uuid.uuid4()),
                    project_id=project1.id,
                    parcel_id=None,
                    title="Good faith negotiation period ends",
                    due_at=datetime.utcnow() + timedelta(days=30),
                    timezone="America/Chicago",
                )
            )
            db.add(
                models.Deadline(
                    id=str(uuid.uuid4()),
                    project_id=project1.id,
                    parcel_id=parcel2_id,
                    title="Initial contact deadline",
                    due_at=datetime.utcnow() + timedelta(days=3),
                    timezone="America/Chicago",
                )
            )
            db.add(
                models.Deadline(
                    id=str(uuid.uuid4()),
                    project_id=project2.id,
                    parcel_id=None,
                    title="Project kickoff milestone",
                    due_at=datetime.utcnow() + timedelta(days=14),
                    timezone="America/Chicago",
                )
            )

            # === Users (password ``devpass123`` for local demos) ===
            from passlib.context import CryptContext

            _pc = CryptContext(schemes=["bcrypt"], deprecated="auto")
            _dev_pw = _pc.hash("devpass123")

            db.add(
                models.User(
                    id="COUNSEL-001",
                    email="counsel@example.com",
                    persona=models.Persona.IN_HOUSE_COUNSEL,
                    full_name="Alicia Attorney",
                    firm_id=models.DEFAULT_FIRM_ID,
                    password_hash=_dev_pw,
                )
            )
            db.add(
                models.User(
                    id="AGENT-001",
                    email="agent@example.com",
                    persona=models.Persona.LAND_AGENT,
                    full_name="Bob Agent",
                    firm_id=models.DEFAULT_FIRM_ID,
                    password_hash=_dev_pw,
                )
            )
            db.add(
                models.User(
                    id="OUTSIDE-001",
                    email="outside@example.com",
                    persona=models.Persona.OUTSIDE_COUNSEL,
                    full_name="Oscar Outside",
                    firm_id=models.DEFAULT_FIRM_ID,
                    password_hash=_dev_pw,
                )
            )
            db.add(
                models.User(
                    id="LANDOWNER-001",
                    email="owner@example.com",
                    persona=models.Persona.LANDOWNER,
                    full_name="Riverbend Owner",
                    firm_id=models.DEFAULT_FIRM_ID,
                    password_hash=_dev_pw,
                )
            )
            db.add(
                models.User(
                    id="PLATFORM-001",
                    email="admin@landgrant.local",
                    persona=models.Persona.PLATFORM_ADMIN,
                    full_name="Pat Platform",
                    firm_id=models.DEFAULT_FIRM_ID,
                    password_hash=_dev_pw,
                )
            )
            # Persist users before the grants that FK-reference them.
            db.flush()

            db.add(
                models.ParcelAccessGrant(
                    id=str(uuid.uuid4()),
                    parcel_id=parcel1_id,
                    user_id="OUTSIDE-001",
                    grantee_email="outside@example.com",
                    scope_persona=models.Persona.OUTSIDE_COUNSEL.value,
                    firm_id=models.DEFAULT_FIRM_ID,
                )
            )
            db.add(
                models.ParcelAccessGrant(
                    id=str(uuid.uuid4()),
                    parcel_id=parcel1_id,
                    grantee_email="owner@example.com",
                    scope_persona=models.Persona.LANDOWNER.value,
                    firm_id=models.DEFAULT_FIRM_ID,
                )
            )

            try:
                _seed_library_templates(db)
            except Exception:
                logger.exception("template library seed failed; continuing demo seed")

            db.commit()
        except Exception:
            # DB may be unavailable or out of space; do not block API startup,
            # but log so silent seed failures are diagnosable.
            logger.exception("dev seed failed; rolling back demo data")
            db.rollback()
            return
    finally:
        db.close()


@app.get("/")
def root():
    return {"app": settings.app_name, "environment": settings.environment}


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
def readyz() -> dict[str, str]:
    _assert_database_ready()
    return {"status": "ready"}
