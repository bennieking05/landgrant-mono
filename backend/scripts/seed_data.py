"""Seed the local Postgres instance with comprehensive stub data for manual testing."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from app.db.session import SessionLocal, Base, engine
from app.db import models
from app.db.models import ProjectStage, Persona


def seed() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # === Projects ===
        project1 = models.Project(
            id="PRJ-001",
            name="Utility Corridor Expansion",
            jurisdiction_code="TX",
            stage=ProjectStage.NEGOTIATION,
            risk_score=35,
            next_deadline_at=datetime.utcnow() + timedelta(days=12),
        )
        project2 = models.Project(
            id="PRJ-002",
            name="Highway 281 Widening",
            jurisdiction_code="TX",
            stage=ProjectStage.INTAKE,
            risk_score=20,
            next_deadline_at=datetime.utcnow() + timedelta(days=30),
        )
        db.merge(project1)
        db.merge(project2)

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
        db.merge(parcel1)
        db.merge(parcel2)
        db.merge(parcel3)
        db.merge(parcel4)
        db.merge(parcel5)
        
        # Flush to ensure parcels exist before dependent entities
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
        db.merge(owner1)
        db.merge(owner2)
        db.merge(owner3)

        # === Parcel-Party relationships ===
        db.merge(models.ParcelParty(parcel_id="PARCEL-001", party_id="OWNER-001", relationship_type="owner"))
        db.merge(models.ParcelParty(parcel_id="PARCEL-002", party_id="OWNER-002", relationship_type="owner"))
        db.merge(models.ParcelParty(parcel_id="PARCEL-003", party_id="OWNER-002", relationship_type="owner"))
        db.merge(models.ParcelParty(parcel_id="PARCEL-004", party_id="OWNER-003", relationship_type="owner"))
        db.merge(models.ParcelParty(parcel_id="PARCEL-005", party_id="OWNER-003", relationship_type="owner"))

        # === Templates ===
        template = models.Template(
            id="fol",
            version="1.0.0",
            locale="en-US",
            jurisdiction="TX",
            variables_schema={"owner_name": {"type": "string"}},
        )
        db.merge(template)

        # === Documents (for title instruments) ===
        doc1_id = "DOC-TITLE-001"
        doc2_id = "DOC-TITLE-002"
        db.merge(models.Document(
            id=doc1_id,
            doc_type="title_instrument",
            version="1.0.0",
            sha256="abc123def456",
            storage_path="local_storage/title/PARCEL-001/deed.pdf",
            metadata_json={"filename": "deed.pdf", "content_type": "application/pdf"},
        ))
        db.merge(models.Document(
            id=doc2_id,
            doc_type="title_instrument",
            version="1.0.0",
            sha256="xyz789abc123",
            storage_path="local_storage/title/PARCEL-001/survey.pdf",
            metadata_json={"filename": "survey.pdf", "content_type": "application/pdf"},
        ))

        # === Communications (multiple channels) ===
        db.merge(models.Communication(
            id="COMM-001",
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
        db.merge(models.Communication(
            id="COMM-002",
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
        db.merge(models.Communication(
            id="COMM-003",
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
        db.merge(models.Communication(
            id="COMM-004",
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
        db.merge(models.RuleResult(
            id="RULE-001",
            parcel_id="PARCEL-001",
            project_id=project1.id,
            rule_id="valuation_threshold",
            version="1.0.0",
            citation="Tex. Prop. Code §21.0113",
            payload={"parcel.assessed_value": 300000},
        ))
        db.merge(models.RuleResult(
            id="RULE-002",
            parcel_id="PARCEL-001",
            project_id=project1.id,
            rule_id="good_faith_meeting",
            version="1.0.0",
            citation="Tex. Prop. Code §21.0114",
            payload={"meeting_scheduled": True, "meeting_date": "2026-01-15"},
        ))
        db.merge(models.RuleResult(
            id="RULE-003",
            parcel_id="PARCEL-002",
            project_id=project1.id,
            rule_id="valuation_threshold",
            version="1.0.0",
            citation="Tex. Prop. Code §21.0113",
            payload={"parcel.assessed_value": 450000},
        ))

        # === Title Instruments ===
        db.merge(models.TitleInstrument(
            id="TITLE-001",
            parcel_id="PARCEL-001",
            document_id=doc1_id,
            ocr_payload={"confidence": 0.92, "entities": ["grantor", "grantee", "legal_description"], "source": "azure_form_recognizer"},
            metadata_json={"instrument_type": "warranty_deed", "recorded_date": "2020-03-15"},
            created_at=datetime.utcnow(),
        ))
        db.merge(models.TitleInstrument(
            id="TITLE-002",
            parcel_id="PARCEL-001",
            document_id=doc2_id,
            ocr_payload={"confidence": 0.88, "entities": ["surveyor", "boundaries"], "source": "azure_form_recognizer"},
            metadata_json={"instrument_type": "survey", "survey_date": "2019-11-20"},
            created_at=datetime.utcnow(),
        ))

        # === Appraisals ===
        db.merge(models.Appraisal(
            id="APPRAISAL-001",
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
        db.merge(models.Deadline(
            id="DEADLINE-001",
            project_id=project1.id,
            parcel_id="PARCEL-001",
            title="Final offer response due",
            due_at=datetime.utcnow() + timedelta(days=7),
            timezone="America/Chicago",
        ))
        db.merge(models.Deadline(
            id="DEADLINE-002",
            project_id=project1.id,
            parcel_id=None,
            title="Good faith negotiation period ends",
            due_at=datetime.utcnow() + timedelta(days=30),
            timezone="America/Chicago",
        ))
        db.merge(models.Deadline(
            id="DEADLINE-003",
            project_id=project1.id,
            parcel_id="PARCEL-002",
            title="Initial contact deadline",
            due_at=datetime.utcnow() + timedelta(days=3),
            timezone="America/Chicago",
        ))
        db.merge(models.Deadline(
            id="DEADLINE-004",
            project_id=project2.id,
            parcel_id=None,
            title="Project kickoff milestone",
            due_at=datetime.utcnow() + timedelta(days=14),
            timezone="America/Chicago",
        ))

        # === Budgets ===
        db.merge(models.Budget(
            id="BUDGET-001",
            project_id=project1.id,
            cap_amount=250000,
            actual_amount=175000,
            variance=-75000,
        ))
        db.merge(models.Budget(
            id="BUDGET-002",
            project_id=project2.id,
            cap_amount=500000,
            actual_amount=50000,
            variance=-450000,
        ))

        # === Users ===
        # Stub user for unauthenticated requests (used by get_current_user dependency)
        db.merge(models.User(
            id="stub",
            email="stub@example.com",
            persona=Persona.LAND_AGENT,
            full_name="Stub User (Testing)",
        ))
        db.merge(models.User(
            id="COUNSEL-001",
            email="counsel@example.com",
            persona=Persona.IN_HOUSE_COUNSEL,
            full_name="Alicia Attorney",
        ))
        db.merge(models.User(
            id="AGENT-001",
            email="agent@example.com",
            persona=Persona.LAND_AGENT,
            full_name="Bob Agent",
        ))
        db.merge(models.User(
            id="OUTSIDE-001",
            email="outside@lawfirm.com",
            persona=Persona.OUTSIDE_COUNSEL,
            full_name="Charlie Counsel",
        ))

        db.commit()
        print("Seed completed successfully")
        print("  - 2 projects")
        print("  - 5 parcels")
        print("  - 3 owners")
        print("  - 4 communications")
        print("  - 3 rule results")
        print("  - 2 title instruments")
        print("  - 1 appraisal")
        print("  - 4 deadlines")
        print("  - 2 budgets")
        print("  - 3 users")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
