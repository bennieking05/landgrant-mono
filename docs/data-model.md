# Data Model

> **Source**: Software Development Agreement - Exhibit A & B  
> **Updated**: January 24, 2026  
> **Implementation**: `backend/app/db/models.py`

---

## Overview

The LandRight MVP data model is organized into functional domains aligned with Agreement Section 3.2 MVP Scope. Each entity includes agreement reference for traceability.

---

## Core Entities (Agreement Section 3.2)

### Projects & Parcels (Section 3.2(a))

- **`Project`**: Utility/pipeline program that groups parcels
  - `jurisdiction_code`, `stage`, `risk_score`, `next_deadline_at`
  - Relationships: parcels, budgets, alignments

- **`Parcel`**: Individual land parcel with PostGIS geometry
  - `county_fips`, `stage`, `risk_score`, `geom` (JSON/PostGIS)
  - `ParcelStage` enum: intake → appraisal → offer_pending → offer_sent → negotiation → closing/litigation → closed
  - Relationships: project, parties, communications, rule_results

- **`Party`**: Normalized person/org table
  - `role`: owner, lienholder, agent, counsel
  - Many-to-many with Parcel via `ParcelParty`

- **`ParcelParty`**: Junction table for parcel-party relationships
  - `relationship_type`: owner, co-owner, lienholder, etc.

### Notices & Service Engine (Section 3.2(b))

- **`Notice`**: Statutory notices per parcel
  - `notice_type`: initial_outreach, offer, statutory, final_offer, possession
  - `method`, `date_issued`, `status`, `statutory_citation`
  - Links to: document, template, service_attempts

- **`ServiceAttempt`**: Service attempts for each notice
  - `method`: mail, certified_mail, personal_service, posting, publication
  - `outcome`: pending, delivered, refused, undeliverable, no_answer
  - `proof_document_id`, `server_affidavit_id`

### Right-of-Entry Management (Section 3.2(c))

- **`ROE`**: Right-of-Entry agreements
  - `effective_date`, `expiry_date`, `status`
  - `conditions`, `permitted_activities`, `access_windows`
  - Relationships: field_events

- **`ROEFieldEvent`**: Field check-in/check-out events
  - `event_type`: check_in, check_out
  - `latitude`, `longitude`, `notes`, `photo_document_ids`

### Litigation Calendar (Section 3.2(d))

- **`LitigationCase`**: Litigation cases linked to parcels
  - `cause_number`, `court`, `is_quick_take` flag
  - `status`: not_filed → filed → served → commissioners_hearing → order_of_possession → trial → appeal → settled → closed
  - `lead_counsel_internal`, `lead_counsel_outside`
  - Key dates: filed, commissioners_hearing, possession_order, trial

- **`Deadline`**: Calendar deadlines for projects/cases
  - `title`, `due_at`, `timezone`
  - Links to: project, parcel

### Title & Curative Tracking (Section 3.2(e))

- **`TitleInstrument`**: Scanned + OCR'd title documents
  - `metadata_json`, `ocr_payload`
  - Links to: parcel, document

- **`CurativeItem`**: Title curative items
  - `item_type`: missing_heir, unreleased_lien, variance, etc.
  - `severity`: low, medium, high, critical
  - `responsible_party`, `due_date`, `status`
  - `status`: open → in_progress → resolved/waived

### Payment Ledger (Section 3.2(f))

- **`Offer`**: Negotiation offers and counteroffers
  - `offer_type`: initial, counteroffer, final, settlement
  - `amount`, `terms`, `status`
  - `source`: internal, landowner
  - NOTE: Amount stored as data only - no valuation computation (per Section 3.3(a))

- **`PaymentLedger`**: Per-parcel payment status tracking
  - `status`: not_started → initial_offer_sent → counteroffer_received → agreement_in_principle → payment_instruction_sent → payment_cleared
  - `current_offer_id`, `settlement_offer_id`
  - `status_history` JSON array

### Communications & Audit (Section 3.2(g))

- **`Communication`**: Omnichannel log per parcel
  - `channel`: email, SMS, portal, certified_mail
  - `direction`, `delivery_status`, `delivery_proof`
  - `sla_due_at`, `hash` for integrity

- **`AuditEvent`**: Append-only audit log
  - `actor_persona`, `action`, `resource`
  - `payload`, `hash` for tamper-evidence

### GIS Alignment & Segmentation (Section 3.2(h))

- **`Alignment`**: Project alignments (routes)
  - `name`, `alignment_type`, `geometry` (GeoJSON LineString)
  - `total_length_miles`, `total_parcels`
  - Relationships: segments

- **`Segment`**: Alignment segments linked to parcels
  - `segment_number`, `geometry`
  - `ed_status`: not_started → surveyed → negotiation → acquired → condemned → closed
  - `acquisition_type`: fee, permanent_easement, temporary_easement
  - `length_feet`, `width_feet`, `area_sqft`

---

## Supporting Entities

### Documents & Templates

- **`Document`**: Generated templates, uploads, binder exports
  - `doc_type`, `version`, `sha256`, `storage_path`
  - `privilege`: privileged, non_privileged

- **`Template`**: Document templates with variable schema
  - `version`, `locale`, `jurisdiction`
  - `variables_schema`, `redactions`, `classifications`

### Appraisals

- **`Appraisal`**: Appraisal data (client-provided only per Section 3.3(a))
  - `completed_at`, `value`, `comps`, `summary`
  - NOTE: No independent valuation modeling

### Workflows & Tasks

- **`Task`**: Workflow tasks with persona ownership
  - `title`, `assigned_to`, `persona`, `due_at`, `status`

- **`Budget`**: Per-project budget tracking
  - `cap_amount`, `actual_amount`, `variance`

### Identity & Access

- **`User`**: System users
  - `email`, `persona`, `full_name`
  - `Persona` enum: landowner, land_agent, in_house_counsel, outside_counsel, admin

- **`Permission`**: Role-based grants
  - `resource`, `action`, `scope`

- **`PortalInvite`**: Landowner portal access tokens
  - `token_sha256`, `expires_at`, `verified_at`
  - `failed_attempts`, `last_failed_at` for rate limiting

- **`StatusChange`**: Status change audit trail
  - `old_status`, `new_status`, `reason`, `hash`

### Rules Engine

- **`RuleResult`**: Deterministic rule outputs
  - `rule_id`, `version`, `citation`, `payload`
  - `evidence_pointer` for audit trail

- **`RequirementPack`**: Versioned jurisdiction requirements
  - `jurisdiction`, `version`, `yaml_content`
  - `status`: draft → validating → validated → active → deprecated

- **`Requirement`**: Individual requirements in canonical schema
  - `topic`, `trigger_event`, `required_action`
  - `deadline_rule`, `deadline_days`, `citations`

---

## AI & Evidence Entities

### AI Decision Tracking

- **`AIDecision`**: Log of AI agent decisions
  - `agent_type`, `context_hash`, `confidence`
  - `reviewed_by`, `review_outcome`

- **`AIEvent`**: Comprehensive AI telemetry
  - `prompt_hash`, `model`, `inputs_json`, `outputs_json`
  - `latency_ms`, `total_tokens`, `cost_estimate_usd`

- **`EscalationRequest`**: Human review requests
  - `reason`, `priority`, `status`, `resolution`

### Citation & Provenance

- **`Source`**: Authoritative legal sources
  - `authority_level`: constitution, statute, case_law, regulation
  - `content_hash`, `raw_text_snippet`

- **`Citation`**: Links claims to sources
  - `span_start`, `span_end`, `snippet_hash`
  - `verification_status`: pending, verified, disputed

### Document QA

- **`QAReport`**: QA check results per document
  - `risk_level`: green, yellow, red
  - `checks_passed`, `checks_failed`, `checks_warned`

- **`QACheck`**: Individual QA check results
  - `check_type`: required_clause, name_consistency, deadline_accuracy, etc.

### Approval Workflow

- **`Approval`**: Human approval tracking
  - `entity_type`, `action`, `status`
  - `content_hash`, `audit_trail`

---

## Entity Relationship Diagram

```
Project (1) ──┬── (*) Parcel ──┬── (*) Notice ──── (*) ServiceAttempt
              │                ├── (*) ROE ──────── (*) ROEFieldEvent
              │                ├── (*) LitigationCase
              │                ├── (*) TitleInstrument
              │                ├── (*) CurativeItem
              │                ├── (*) Offer
              │                ├── (1) PaymentLedger
              │                ├── (*) Communication
              │                └── (*) ParcelParty ── Party
              │
              ├── (*) Alignment ── (*) Segment ── Parcel
              ├── (*) Deadline
              └── (*) Budget
```

---

## Agreement Traceability
`
| Section | Entity Coverage |
|---------|-----------------|
| 3.2(a) Projects/Parcels | Project, Parcel, Party, ParcelParty |
| 3.2(b) Notices/Service | Notice, ServiceAttempt |
| 3.2(c) ROE Management | ROE, ROEFieldEvent |
| 3.2(d) Litigation Calendar | LitigationCase, Deadline |
| 3.2(e) Title/Curative | TitleInstrument, CurativeItem |
| 3.2(f) Payment Ledger | Offer, PaymentLedger |
| 3.2(g) Communications | Communication, AuditEvent |
| 3.2(h) GIS Alignment | Alignment, Segment |

---

## Implementation Notes

1. All entities are defined in `backend/app/db/models.py`
2. PostGIS geometry stored as JSON (use actual PostGIS in production)
3. Audit hashes use SHA-256 for tamper-evidence
4. All timestamps use UTC (datetime.utcnow)
5. Soft deletes via status fields, not actual deletion
