from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    cases,
    templates,
    ai,
    health,
    workflows,
    integrations,
    portal,
    communications,
    packet,
    rules,
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
    summaries,
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
from app.telemetry import configure_tracing

settings = get_settings()
configure_tracing()

app = FastAPI(title="LandRight API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(cases.router)
app.include_router(templates.router)
app.include_router(ai.router)
app.include_router(workflows.router)
app.include_router(integrations.router)
app.include_router(portal.router)
app.include_router(communications.router)
app.include_router(packet.router)
app.include_router(rules.router)
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
app.include_router(summaries.router)
app.include_router(rag.router)
app.include_router(copilot.router)
app.include_router(analytics.router)

# Real-time WebSocket
app.include_router(websocket.router)

# ML Predictions
app.include_router(predictions.router)

# Task Management
app.include_router(tasks.router)


@app.on_event("startup")
def bootstrap_dev_db() -> None:
    """
    Local-dev convenience so the app is usable without manual migrations/seed steps.
    In production we should use Alembic migrations instead.
    """
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        # If the DB isn't available, we still want the API process to start so
        # stub-only endpoints can work; DB-backed routes will return errors.
        return

    if settings.environment != "dev":
        return

    db = SessionLocal()
    try:
        try:
            # Seed a comprehensive demo dataset if missing.
            if db.get(models.Project, "PRJ-001"):
                return

            from datetime import datetime, timedelta
            import uuid

            # === Projects ===
            project1 = models.Project(
                id="PRJ-001",
                name="Utility Corridor Expansion",
                jurisdiction_code="TX",
                stage=models.ProjectStage.NEGOTIATION,
                risk_score=35,
                next_deadline_at=datetime.utcnow() + timedelta(days=12),
            )
            project2 = models.Project(
                id="PRJ-002",
                name="Highway 281 Widening",
                jurisdiction_code="TX",
                stage=models.ProjectStage.INTAKE,
                risk_score=20,
                next_deadline_at=datetime.utcnow() + timedelta(days=30),
            )
            db.add(project1)
            db.add(project2)

            # === Parcels (5 total with varied risk/deadline) ===
            parcel1 = models.Parcel(
                id="PARCEL-001",
                project_id=project1.id,
                county_fips="48439",
                stage="negotiation",
                risk_score=40,
                next_deadline_at=datetime.utcnow() + timedelta(days=7),
            )
            parcel2 = models.Parcel(
                id="PARCEL-002",
                project_id=project1.id,
                county_fips="48439",
                stage="intake",
                risk_score=75,
                next_deadline_at=datetime.utcnow() + timedelta(days=3),
            )
            parcel3 = models.Parcel(
                id="PARCEL-003",
                project_id=project1.id,
                county_fips="48439",
                stage="offer_sent",
                risk_score=25,
                next_deadline_at=datetime.utcnow() + timedelta(days=14),
            )
            parcel4 = models.Parcel(
                id="PARCEL-004",
                project_id=project1.id,
                county_fips="48453",
                stage="closed",
                risk_score=10,
                next_deadline_at=None,
            )
            parcel5 = models.Parcel(
                id="PARCEL-005",
                project_id=project2.id,
                county_fips="48029",
                stage="intake",
                risk_score=55,
                next_deadline_at=datetime.utcnow() + timedelta(days=21),
            )
            db.add(parcel1)
            db.add(parcel2)
            db.add(parcel3)
            db.add(parcel4)
            db.add(parcel5)

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
            db.add(models.ParcelParty(parcel_id="PARCEL-001", party_id="OWNER-001", relationship_type="owner"))
            db.add(models.ParcelParty(parcel_id="PARCEL-002", party_id="OWNER-002", relationship_type="owner"))
            db.add(models.ParcelParty(parcel_id="PARCEL-003", party_id="OWNER-002", relationship_type="owner"))
            db.add(models.ParcelParty(parcel_id="PARCEL-004", party_id="OWNER-003", relationship_type="owner"))
            db.add(models.ParcelParty(parcel_id="PARCEL-005", party_id="OWNER-003", relationship_type="owner"))

            # === Communications (multiple channels) ===
            db.add(models.Communication(
                id=str(uuid.uuid4()),
                parcel_id="PARCEL-001",
                project_id=project1.id,
                channel="email",
                direction="outbound",
                content="Final offer delivered",
                delivery_status="delivered",
                delivery_proof={"provider": "SendGrid", "id": "sg_demo_001"},
                sla_due_at=datetime.utcnow() + timedelta(days=3),
                hash="hash-demo-001",
            ))
            db.add(models.Communication(
                id=str(uuid.uuid4()),
                parcel_id="PARCEL-001",
                project_id=project1.id,
                channel="sms",
                direction="outbound",
                content="Reminder: Please review the offer documents",
                delivery_status="delivered",
                delivery_proof={"provider": "Twilio", "id": "SM_demo_001"},
                sla_due_at=datetime.utcnow() + timedelta(days=1),
                hash="hash-demo-002",
            ))
            db.add(models.Communication(
                id=str(uuid.uuid4()),
                parcel_id="PARCEL-001",
                project_id=project1.id,
                channel="certified_mail",
                direction="outbound",
                content="Formal offer packet delivered via certified mail",
                delivery_status="delivered",
                delivery_proof={"provider": "Lob", "tracking": "9400111899223456789012"},
                sla_due_at=datetime.utcnow() + timedelta(days=5),
                hash="hash-demo-003",
            ))
            db.add(models.Communication(
                id=str(uuid.uuid4()),
                parcel_id="PARCEL-002",
                project_id=project1.id,
                channel="email",
                direction="outbound",
                content="Initial contact letter sent",
                delivery_status="pending",
                delivery_proof={"provider": "SendGrid", "id": "sg_demo_002"},
                sla_due_at=datetime.utcnow() + timedelta(days=2),
                hash="hash-demo-004",
            ))

            # === Rule Results ===
            db.add(models.RuleResult(
                id=str(uuid.uuid4()),
                parcel_id="PARCEL-001",
                project_id=project1.id,
                rule_id="valuation_threshold",
                version="1.0.0",
                citation="Tex. Prop. Code §21.0113",
                payload={"parcel.assessed_value": 300000},
            ))
            db.add(models.RuleResult(
                id=str(uuid.uuid4()),
                parcel_id="PARCEL-001",
                project_id=project1.id,
                rule_id="good_faith_meeting",
                version="1.0.0",
                citation="Tex. Prop. Code §21.0114",
                payload={"meeting_scheduled": True, "meeting_date": "2026-01-15"},
            ))
            db.add(models.RuleResult(
                id=str(uuid.uuid4()),
                parcel_id="PARCEL-002",
                project_id=project1.id,
                rule_id="valuation_threshold",
                version="1.0.0",
                citation="Tex. Prop. Code §21.0113",
                payload={"parcel.assessed_value": 450000},
            ))

            # === Budget ===
            db.add(models.Budget(
                id=str(uuid.uuid4()),
                project_id=project1.id,
                cap_amount=250000,
                actual_amount=175000,
                variance=-75000,
            ))
            db.add(models.Budget(
                id=str(uuid.uuid4()),
                project_id=project2.id,
                cap_amount=500000,
                actual_amount=50000,
                variance=-450000,
            ))

            # === Documents (for title instruments) ===
            doc1_id = str(uuid.uuid4())
            doc2_id = str(uuid.uuid4())
            db.add(models.Document(
                id=doc1_id,
                doc_type="title_instrument",
                version="1.0.0",
                sha256="abc123def456",
                storage_path="local_storage/title/PARCEL-001/deed.pdf",
                metadata_json={"filename": "deed.pdf", "content_type": "application/pdf"},
            ))
            db.add(models.Document(
                id=doc2_id,
                doc_type="title_instrument",
                version="1.0.0",
                sha256="xyz789abc123",
                storage_path="local_storage/title/PARCEL-001/survey.pdf",
                metadata_json={"filename": "survey.pdf", "content_type": "application/pdf"},
            ))

            # === Title Instruments ===
            db.add(models.TitleInstrument(
                id=str(uuid.uuid4()),
                parcel_id="PARCEL-001",
                document_id=doc1_id,
                ocr_payload={"confidence": 0.92, "entities": ["grantor", "grantee", "legal_description"], "source": "azure_form_recognizer"},
                metadata_json={"instrument_type": "warranty_deed", "recorded_date": "2020-03-15"},
                created_at=datetime.utcnow(),
            ))
            db.add(models.TitleInstrument(
                id=str(uuid.uuid4()),
                parcel_id="PARCEL-001",
                document_id=doc2_id,
                ocr_payload={"confidence": 0.88, "entities": ["surveyor", "boundaries"], "source": "azure_form_recognizer"},
                metadata_json={"instrument_type": "survey", "survey_date": "2019-11-20"},
                created_at=datetime.utcnow(),
            ))

            # === Appraisals ===
            db.add(models.Appraisal(
                id=str(uuid.uuid4()),
                parcel_id="PARCEL-001",
                value=350000,
                summary="Commercial property with highway frontage. Appraised using sales comparison approach with 3 comparable sales in the area.",
                comps=[
                    {"address": "123 Highway Dr", "sale_price": 340000, "sale_date": "2025-06-15"},
                    {"address": "456 Commerce Blvd", "sale_price": 365000, "sale_date": "2025-08-22"},
                    {"address": "789 Industrial Way", "sale_price": 345000, "sale_date": "2025-09-10"},
                ],
                completed_at=datetime.utcnow() - timedelta(days=5),
            ))

            # === Deadlines ===
            db.add(models.Deadline(
                id=str(uuid.uuid4()),
                project_id=project1.id,
                parcel_id="PARCEL-001",
                title="Final offer response due",
                due_at=datetime.utcnow() + timedelta(days=7),
                timezone="America/Chicago",
            ))
            db.add(models.Deadline(
                id=str(uuid.uuid4()),
                project_id=project1.id,
                parcel_id=None,
                title="Good faith negotiation period ends",
                due_at=datetime.utcnow() + timedelta(days=30),
                timezone="America/Chicago",
            ))
            db.add(models.Deadline(
                id=str(uuid.uuid4()),
                project_id=project1.id,
                parcel_id="PARCEL-002",
                title="Initial contact deadline",
                due_at=datetime.utcnow() + timedelta(days=3),
                timezone="America/Chicago",
            ))
            db.add(models.Deadline(
                id=str(uuid.uuid4()),
                project_id=project2.id,
                parcel_id=None,
                title="Project kickoff milestone",
                due_at=datetime.utcnow() + timedelta(days=14),
                timezone="America/Chicago",
            ))

            # === Users ===
            db.add(models.User(
                id="COUNSEL-001",
                email="counsel@example.com",
                persona=models.Persona.IN_HOUSE_COUNSEL,
                full_name="Alicia Attorney",
            ))
            db.add(models.User(
                id="AGENT-001",
                email="agent@example.com",
                persona=models.Persona.LAND_AGENT,
                full_name="Bob Agent",
            ))

            db.commit()
        except Exception:
            # DB may be unavailable or out of space; do not block API startup.
            db.rollback()
            return
    finally:
        db.close()


@app.get("/")
def root():
    return {"app": settings.app_name, "environment": settings.environment}
