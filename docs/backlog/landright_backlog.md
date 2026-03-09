# LandRight MVP Backlog

> **Source**: Software Development Agreement (Effective Date: January 5, 2026)  
> **Project Fee**: $175,000  
> **MVP Term**: 160 days from Project Start Date  
> **Generated**: January 24, 2026

---

## Overview

This backlog is derived from the Software Development Agreement between LandRight AI, Inc. and NexGen Software Solutions LLC. It covers all functional requirements from Exhibit A (Product Requirements Document) and deliverables from Exhibit B (Milestones, Schedule and Fees).

### Milestone Summary

| Milestone | Name | Target | Fee |
|-----------|------|--------|-----|
| M1 | Technical Design & Backlog Refinement | 30 days | $35,000 |
| M2 | Backend MVP API | 60 days | $26,250 |
| M3 | Frontend Internal Web App | 90 days | $26,250 |
| M4 | Landowner Portal, Negotiation Portal & Comms | 120 days | $26,250 |
| M5 | UAT Completion, Hardening & Production-Ready | 160 days | $26,250 |

### Labels

- `milestone-1` through `milestone-5`: Milestone assignment
- `scope-mvp`: In scope for MVP delivery
- `out-of-scope`: Explicitly excluded from MVP
- `exhibit-a`: Derived from Exhibit A (Product Requirements)
- `exhibit-b`: Derived from Exhibit B (Milestones)
- `backend`, `frontend`, `design`, `uat`: Work type

---

## EPIC 1: Projects & Parcels

**Description**: Core project and parcel management with PostGIS geometry support.  
**Agreement Reference**: Exhibit A - "Projects and Parcels Functionality", Section 3.2(a)

### Stories

#### PP-001: Create and Manage Projects
**Summary**: As a ROW Manager, I can create and manage Projects with core metadata so that I can organize parcels by program/initiative.

**Acceptance Criteria**:
- [ ] Create new Project with: name, owner, state(s), type, target in-service date
- [ ] Edit project metadata
- [ ] List all projects with filtering
- [ ] Associate project with jurisdiction_code

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### PP-002: Import and Manage Parcels
**Summary**: As a ROW Manager, I can import parcels via CSV or add them manually so that project land assets are tracked in the system.

**Acceptance Criteria**:
- [ ] CSV import for bulk parcel creation
- [ ] Manual parcel creation form
- [ ] Each parcel has: internal ID, external ID (e.g., county ID), landowner info, PostGIS geometry
- [ ] Acquisition type field (fee/easement, permanent/temporary)
- [ ] Overall parcel status (planning, pre-condemnation, filed, possession, closed)

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### PP-003: Parcel List and Detail Views (Frontend)
**Summary**: As an internal user, I can view project-level parcel lists and drill down to parcel detail views.

**Acceptance Criteria**:
- [ ] Project-level parcel list with pagination and filtering
- [ ] Parcel detail view showing all metadata
- [ ] Link to related notices, ROEs, title docs, communications
- [ ] Map visualization with parcel polygon

**Labels**: `milestone-3`, `scope-mvp`, `exhibit-a`, `frontend`

---

## EPIC 2: Notices & Service (Legal Playbooks)

**Description**: Record and track notices and service attempts per parcel with per-jurisdiction validation.  
**Agreement Reference**: Exhibit A - "Legal Playbooks – Notices & Service Functionality", Section 3.2(b)

### Stories

#### NS-001: Record Notice Issuance
**Summary**: As a ROW Manager, I can record issuance of notices per parcel so that there is a legal record of all communications.

**Acceptance Criteria**:
- [ ] Add notice with: type (initial outreach, offer, statutory notice), date, method
- [ ] Link notice to source document
- [ ] Notice appears in parcel timeline

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### NS-002: Track Service Attempts
**Summary**: As a ROW Manager, I can track service attempts including method, date, and outcome.

**Acceptance Criteria**:
- [ ] Record service attempt: method (mail, personal service, posting), date, outcome
- [ ] Multiple attempts per notice supported
- [ ] System updates parcel notice/service status automatically

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### NS-003: Per-Jurisdiction Service Validation
**Summary**: As a ROW Manager, I receive flags for obvious service gaps based on jurisdiction rules.

**Acceptance Criteria**:
- [ ] Simple per-jurisdiction checks (e.g., no recorded service after notice, insufficient attempts)
- [ ] Deficiency flags displayed on parcel view
- [ ] Rule validation configurable per state/jurisdiction

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### NS-004: Notice & Service UI
**Summary**: As an internal user, I can log notices and service attempts through the web interface.

**Acceptance Criteria**:
- [ ] "Add Notice" form with type, date, method, document link
- [ ] Service attempt logging form
- [ ] Notice/service status display on parcel detail

**Labels**: `milestone-3`, `scope-mvp`, `exhibit-a`, `frontend`

---

## EPIC 3: Right-of-Entry (ROE) Management

**Description**: Track ROE agreements, expiry dates, conditions, and field access events.  
**Agreement Reference**: Exhibit A - "Right-of-Entry (ROE) Manager Functionality", Section 3.2(c)

### Stories

#### ROE-001: ROE Agreement Tracking
**Summary**: As a ROW Manager, I can track ROE agreements with effective/expiry dates, conditions, and permitted activities.

**Acceptance Criteria**:
- [ ] Create ROE record with: effective date, expiry date, conditions, permitted activities
- [ ] Link ROE to parcel
- [ ] ROE template association

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### ROE-002: Field Check-In/Check-Out
**Summary**: As a field agent, I can capture check-in/check-out events for ROE use.

**Acceptance Criteria**:
- [ ] Record check-in event with timestamp and user
- [ ] Record check-out event with timestamp
- [ ] Events linked to specific ROE

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### ROE-003: ROE Expiry Alerts
**Summary**: As a ROW Manager, I see flags for upcoming or expired ROEs at parcel and project level.

**Acceptance Criteria**:
- [ ] Flag ROEs expiring within configurable threshold (e.g., 30 days)
- [ ] Flag expired ROEs
- [ ] Project-level summary of ROE status

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### ROE-004: ROE Management UI
**Summary**: As an internal user, I can manage ROEs through the web interface.

**Acceptance Criteria**:
- [ ] ROE tab/view on parcel detail
- [ ] Create/edit ROE form
- [ ] Expiry status indicators
- [ ] Check-in/check-out logging UI

**Labels**: `milestone-3`, `scope-mvp`, `exhibit-a`, `frontend`

---

## EPIC 4: Litigation & Case Deadline Calendar

**Description**: Record litigation status, case metadata, and maintain deadline calendar.  
**Agreement Reference**: Exhibit A - "Litigation & Case Deadline Calendar Functionality", Section 3.2(d)

### Stories

#### LIT-001: Litigation Status Tracking
**Summary**: As Legal/Counsel, I can record litigation status per parcel (filed, order of possession, appeal, settled).

**Acceptance Criteria**:
- [ ] Litigation status field on parcel (enum: filed, order of possession, appeal, settled, etc.)
- [ ] Status change history tracked
- [ ] Quick-take vs standard flag (per Agreement Section 3.2(d))

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### LIT-002: Case Metadata
**Summary**: As Legal/Counsel, I can capture case metadata including court, cause number, and lead counsel.

**Acceptance Criteria**:
- [ ] Case record with: court, cause number, lead counsel (in-house), lead counsel (outside), litigation stage
- [ ] Link case to parcel(s)
- [ ] Multiple cases per project supported

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### LIT-003: Case Deadline Calendar
**Summary**: As Legal/Counsel, I can maintain a deadline calendar with filing dates, hearings, motions, and commissioners' hearings.

**Acceptance Criteria**:
- [ ] Create deadline: type, date, description, associated parcel/case
- [ ] Deadline types: filing date, hearing date, motion deadline, commissioners' hearing
- [ ] Association with parcels and cases
- [ ] Manually managed events (per Agreement)

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### LIT-004: Calendar and List Views
**Summary**: As Legal/Counsel, I can view deadlines in calendar and list formats with filtering.

**Acceptance Criteria**:
- [ ] Calendar view by project, case, or date range
- [ ] List view with sorting/filtering
- [ ] "Critical upcoming deadlines" filter
- [ ] iCal export capability

**Labels**: `milestone-3`, `scope-mvp`, `exhibit-a`, `frontend`

---

#### LIT-005: Litigation Calendar UI (Milestone 4)
**Summary**: As Legal/Counsel, I can use the full litigation calendar UI with cross-links to parcel and project screens.

**Acceptance Criteria**:
- [ ] Full calendar UI implementation
- [ ] Cross-links to parcel detail
- [ ] Cross-links to project views
- [ ] Deadline creation from UI

**Labels**: `milestone-4`, `scope-mvp`, `exhibit-b`, `frontend`

---

## EPIC 5: Title & Curative Tracking

**Description**: Store title documents, track curative items, and provide title report analytics.  
**Agreement Reference**: Exhibit A - "Title & Curative Tracker + Title Report Analytics Functionality"

### Stories

#### TIT-001: Title Document Storage
**Summary**: As a ROW Manager, I can store title documents per parcel with metadata.

**Acceptance Criteria**:
- [ ] Upload title documents (reports, opinions, recorded instruments)
- [ ] Metadata: type, date, jurisdiction, source, version
- [ ] Link to parcel
- [ ] Document versioning

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### TIT-002: Curative Item Tracking
**Summary**: As a ROW Manager, I can track curative items with description, responsible party, due date, and status.

**Acceptance Criteria**:
- [ ] Create curative item: description (e.g., missing heir, unreleased lien, variance issue)
- [ ] Assign responsible party
- [ ] Set due date
- [ ] Status tracking: open, in progress, resolved

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### TIT-003: Title Report Analytics (MVP)
**Summary**: As an internal user, I can view title report analytics showing counts, types, and severity of curative issues.

**Acceptance Criteria**:
- [ ] Counts and types of curative issues by project or segment
- [ ] Identify parcels with multiple or severe curative issues
- [ ] High-level summaries: lienholder counts, unreleased encumbrances
- [ ] Summary views for analytics queries

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### TIT-004: Title & Curative UI
**Summary**: As an internal user, I can manage title documents and curative items through the web interface.

**Acceptance Criteria**:
- [ ] Title tab/view on parcel detail
- [ ] Document upload form
- [ ] Curative item list with CRUD operations
- [ ] Status indicators and filtering

**Labels**: `milestone-3`, `scope-mvp`, `exhibit-a`, `frontend`

---

#### TIT-005: Title Analytics Dashboard
**Summary**: As an internal user, I can view title analytics in dashboard format.

**Acceptance Criteria**:
- [ ] Tabular view of curative issue counts
- [ ] Basic charts for issue distribution
- [ ] Filter by project, segment, status
- [ ] Export capabilities

**Labels**: `milestone-3`, `scope-mvp`, `exhibit-a`, `frontend`

---

## EPIC 6: Payment & Negotiation Module

**Description**: Track payment status and negotiation workflow (offers, counteroffers) without valuation logic.  
**Agreement Reference**: Exhibit A - "Payment & Negotiation Module (Negotiation Portal) Functionality", Section 3.2(f)

### Stories

#### PAY-001: Payment Ledger (Status)
**Summary**: As a ROW Manager, I can track offer/payment status per parcel.

**Acceptance Criteria**:
- [ ] Payment status field: Initial offer sent, Counteroffer received, Agreement in principle, Payment instruction sent, Payment cleared
- [ ] Status history tracked
- [ ] No independent valuation computation (per Agreement exclusions)

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### PAY-002: Offer and Settlement Data
**Summary**: As a ROW Manager, I can store offer and settlement amounts as data fields.

**Acceptance Criteria**:
- [ ] Initial offer amount field
- [ ] Settlement amount field
- [ ] Key terms field (text/JSON)
- [ ] Date fields for each offer stage

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### PAY-003: Offer/Counteroffer History
**Summary**: As Legal/Finance, I can view the complete offer/counteroffer history for a parcel.

**Acceptance Criteria**:
- [ ] Create initial offer: amount, terms, date
- [ ] Record counteroffer: amount, terms, date, source (landowner/internal)
- [ ] Full history log with timestamps
- [ ] System logs each negotiation step

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### PAY-004: Payment & Negotiation UI
**Summary**: As an internal user, I can manage offers and payment status through the web interface.

**Acceptance Criteria**:
- [ ] Payment/Negotiation tab on parcel detail
- [ ] Create/edit offer form
- [ ] Counteroffer logging
- [ ] Status update controls
- [ ] History view

**Labels**: `milestone-3`, `scope-mvp`, `exhibit-a`, `frontend`

---

## EPIC 7: Landowner Portal

**Description**: Secure portal for landowners to view status, documents, upload files, and participate in negotiations.  
**Agreement Reference**: Exhibit A - "Landowner Portal: Status and Uploads"

### Stories

#### LP-001: Tokenized Secure Access
**Summary**: As a landowner, I can access the portal via tokenized links without self-registration.

**Acceptance Criteria**:
- [ ] Token-based access links (no open self-registration in MVP)
- [ ] Time-limited tokens
- [ ] Secure session management
- [ ] Access logging

**Labels**: `milestone-4`, `scope-mvp`, `exhibit-a`, `backend`

---

#### LP-002: Status Display
**Summary**: As a landowner, I can see plain-language status summarizing where my parcel is in the ED/LA process.

**Acceptance Criteria**:
- [ ] Plain-language status summary
- [ ] Key milestone indicators
- [ ] Next steps information

**Labels**: `milestone-4`, `scope-mvp`, `exhibit-a`, `frontend`

---

#### LP-003: Document List and Download
**Summary**: As a landowner, I can view and download key documents (notices, ROEs, approved documents).

**Acceptance Criteria**:
- [ ] Document list with download links
- [ ] Filter by document type
- [ ] Only approved/released documents visible

**Labels**: `milestone-4`, `scope-mvp`, `exhibit-a`, `frontend`

---

#### LP-004: Landowner Uploads
**Summary**: As a landowner, I can upload information and documents through the portal.

**Acceptance Criteria**:
- [ ] File upload interface
- [ ] Supported file types and size limits (determined during design)
- [ ] Uploads associated with parcel and flagged for review
- [ ] Basic validation and security scanning

**Labels**: `milestone-4`, `scope-mvp`, `exhibit-a`, `backend`, `frontend`

---

#### LP-005: Negotiation Portal (Landowner View)
**Summary**: As a landowner, I can view offers and respond via the portal.

**Acceptance Criteria**:
- [ ] View initial offer with clear summary language
- [ ] Response options: accept, counter, request changes
- [ ] Counteroffer submission with amount and terms
- [ ] System logs response and updates negotiation status

**Labels**: `milestone-4`, `scope-mvp`, `exhibit-a`, `frontend`

---

#### LP-006: Portal Audit Logging
**Summary**: All landowner interactions are recorded in parcel-level communications and audit logs.

**Acceptance Criteria**:
- [ ] Log all portal sessions
- [ ] Log all uploads with metadata
- [ ] Log all negotiation responses
- [ ] Audit trail exportable

**Labels**: `milestone-4`, `scope-mvp`, `exhibit-a`, `backend`

---

## EPIC 8: Communications

**Description**: Internal communications log and one-to-many landowner communications.  
**Agreement Reference**: Exhibit A - "Communications & Landowner Communications (One-to-Many) Functionality"

### Stories

#### COM-001: Internal Communications Log
**Summary**: As an internal user, I can log communications (phone calls, emails, meetings, site visits, portal interactions) per parcel.

**Acceptance Criteria**:
- [ ] Log entry with: type, date, participants, summary, related documents
- [ ] Communication types: phone, email, in-person, site visit, portal interaction
- [ ] Link to parcel record

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### COM-002: Batch Communications (One-to-Many)
**Summary**: As an internal user, I can send batch communications to multiple parcels/owners.

**Acceptance Criteria**:
- [ ] Select multiple parcels/owners for batch send
- [ ] Email through integrated provider (SendGrid, SES, or equivalent)
- [ ] Mail-merge-style export (PDF/letter export)
- [ ] Template selection for batch sends

**Labels**: `milestone-4`, `scope-mvp`, `exhibit-a`, `backend`

---

#### COM-003: Communication Event Logging
**Summary**: Each communication send event is logged at the parcel level.

**Acceptance Criteria**:
- [ ] Log send event: date, communication type, template used, result
- [ ] Delivery status tracking (where provider allows)
- [ ] Link to generated document

**Labels**: `milestone-4`, `scope-mvp`, `exhibit-a`, `backend`

---

#### COM-004: Communications UI
**Summary**: As an internal user, I can manage communications through the web interface.

**Acceptance Criteria**:
- [ ] Communications tab/view on parcel detail
- [ ] Add communication log entry form
- [ ] View communication history

**Labels**: `milestone-3`, `scope-mvp`, `exhibit-a`, `frontend`

---

#### COM-005: Batch Communications UI
**Summary**: As an internal user, I can select recipients and send batch communications.

**Acceptance Criteria**:
- [ ] Recipient selection (multi-select parcels/owners)
- [ ] Template selection
- [ ] Preview before send
- [ ] Send confirmation and logging

**Labels**: `milestone-4`, `scope-mvp`, `exhibit-a`, `frontend`

---

## EPIC 9: Documents & Templates

**Description**: Central document repository and template generator for IOL/FOL/Easements.  
**Agreement Reference**: Exhibit A - "Document Management & Template Generator (IOL/FOL/Easements) Functionality"

### Stories

#### DOC-001: Central Document Repository
**Summary**: As an internal user, I can store and retrieve documents associated with projects and parcels.

**Acceptance Criteria**:
- [ ] Document types: notices, ROEs, title reports, orders, easements
- [ ] Metadata tagging: type, date, jurisdiction, source, version
- [ ] S3-compatible storage backend
- [ ] Document versioning

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### DOC-002: Template Storage
**Summary**: As Legal, I can store approved text templates with structured data fields.

**Acceptance Criteria**:
- [ ] Template storage in relational database
- [ ] Template metadata (type, version, approval status)
- [ ] Structured data field definitions (owner name, parcel ID, project name, offer amount, dates)

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### DOC-003: Template Versioning and Approval
**Summary**: As Legal, I can version templates and mark them as approved.

**Acceptance Criteria**:
- [ ] Version tracking for templates
- [ ] Approval workflow (draft → approved)
- [ ] Only approved templates available for generation
- [ ] Audit trail of template changes

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### DOC-004: Document Generation
**Summary**: As an internal user, I can generate documents (PDF or Word) from templates.

**Acceptance Criteria**:
- [ ] Server-side rendering of templates
- [ ] Output formats: PDF, Word
- [ ] Data field substitution
- [ ] Preview before finalization

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### DOC-005: Template Generator (IOL/FOL/Easements)
**Summary**: As Legal, I can generate Initial Offer Letters, Final Offer Letters, and standard easement forms.

**Acceptance Criteria**:
- [ ] IOL template and generation
- [ ] FOL template and generation
- [ ] Standard easement forms (as defined by Client legal team)
- [ ] One-off generation (per parcel)
- [ ] Batch generation as part of communication run

**Labels**: `milestone-4`, `scope-mvp`, `exhibit-a`, `backend`

---

#### DOC-006: Documents & Templates UI
**Summary**: As an internal user, I can manage documents and templates through the web interface.

**Acceptance Criteria**:
- [ ] Documents tab/view on parcel detail
- [ ] Document upload and metadata editing
- [ ] Template browser (list, preview)
- [ ] Template creation and editing (Legal role)

**Labels**: `milestone-3`, `scope-mvp`, `exhibit-a`, `frontend`

---

#### DOC-007: End-to-End Template Generation Flow (M4)
**Summary**: As an internal user, I can complete the full flow from template selection to document dispatch.

**Acceptance Criteria**:
- [ ] Select template → fill data → generate → preview → dispatch
- [ ] Email export option
- [ ] Mail-merge export option
- [ ] Logging of generated documents

**Labels**: `milestone-4`, `scope-mvp`, `exhibit-b`, `frontend`

---

## EPIC 10: GIS Alignment & Segmentation

**Description**: Represent project alignments, link to parcels, and visualize on maps.  
**Agreement Reference**: Exhibit A - "GIS Alignment & Parcel Segmentation Functionality", Section 3.2(h)

### Stories

#### GIS-001: Alignment Import
**Summary**: As a ROW Manager, I can import project alignments (e.g., pipeline routes).

**Acceptance Criteria**:
- [ ] Import alignment geometry (GeoJSON, shapefile, or equivalent)
- [ ] Link alignment to project
- [ ] Store in PostGIS

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### GIS-002: Segment Generation
**Summary**: As a ROW Manager, I can generate segments from alignments and link them to parcels.

**Acceptance Criteria**:
- [ ] Generate segments from alignment
- [ ] Link parcels to segments
- [ ] Per-segment ED status tracking

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### GIS-003: Map Visualization
**Summary**: As an internal user, I can view basic maps with parcel polygons and alignment lines.

**Acceptance Criteria**:
- [ ] Map component with parcel polygons
- [ ] Alignment line overlay
- [ ] Basic zoom/pan controls
- [ ] Click-to-select parcel

**Labels**: `milestone-3`, `scope-mvp`, `exhibit-a`, `frontend`

---

#### GIS-004: Map Filtering
**Summary**: As an internal user, I can filter and color parcels on the map by status, curative severity, and negotiation status.

**Acceptance Criteria**:
- [ ] Filter by parcel status
- [ ] Filter by curative severity
- [ ] Filter by negotiation status
- [ ] Color coding based on filter

**Labels**: `milestone-3`, `scope-mvp`, `exhibit-a`, `frontend`

---

## EPIC 11: Analytics & Reporting

**Description**: Core analytics dashboards for parcel status, title/curative, negotiation, and appraisal metrics.  
**Agreement Reference**: Exhibit A - "Analytics & Reporting (Including Title/Appraisal Analytics) Functionality"

### Stories

#### ANA-001: Parcel Status Analytics
**Summary**: As an internal user, I can view parcel status distributions by project and segment.

**Acceptance Criteria**:
- [ ] Status distribution charts/tables
- [ ] Filter by project, segment
- [ ] Export capability

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### ANA-002: Title & Curative Analytics
**Summary**: As an internal user, I can view title and curative analytics.

**Acceptance Criteria**:
- [ ] Counts/types of curative issues
- [ ] Curative resolution rates and cycle times
- [ ] Filter by project, segment

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### ANA-003: Negotiation Analytics
**Summary**: As an internal user, I can view negotiation analytics.

**Acceptance Criteria**:
- [ ] Count of offers/counteroffers
- [ ] Time-to-agreement metrics (where available)
- [ ] Filter by project, segment

**Labels**: `milestone-4`, `scope-mvp`, `exhibit-b`, `backend`

---

#### ANA-004: Appraisal Analytics (MVP)
**Summary**: As an internal user, I can view high-level appraisal summaries based on client-provided data.

**Acceptance Criteria**:
- [ ] Count of parcels with appraisals completed
- [ ] Appraisal ranges by segment
- [ ] Average appraised values by segment
- [ ] No independent valuation modeling (per exclusions)

**Labels**: `milestone-4`, `scope-mvp`, `exhibit-b`, `backend`

---

#### ANA-005: Analytics Dashboard UI
**Summary**: As an internal user, I can view analytics in dashboard format with tables and charts.

**Acceptance Criteria**:
- [ ] Dashboard page with tabular views
- [ ] Simple charts (bar, pie, line)
- [ ] Export to CSV/PDF

**Labels**: `milestone-3`, `scope-mvp`, `exhibit-a`, `frontend`

---

#### ANA-006: Expanded Analytics (M4)
**Summary**: As an internal user, I can view expanded analytics including negotiation and appraisal metrics.

**Acceptance Criteria**:
- [ ] Negotiation metrics dashboard
- [ ] Appraisal metrics dashboard (using client-provided data only)
- [ ] Combined views across analytics types

**Labels**: `milestone-4`, `scope-mvp`, `exhibit-b`, `frontend`

---

## EPIC 12: Authentication & Authorization

**Description**: JWT-based auth, role model, and tokenized landowner access.  
**Agreement Reference**: Exhibit A - "Technical Overview - Authentication & Authorization"

### Stories

#### AUTH-001: JWT Authentication (Internal Users)
**Summary**: Internal and outside-counsel users authenticate via JWT-based auth.

**Acceptance Criteria**:
- [ ] JWT token generation and validation
- [ ] Token refresh mechanism
- [ ] Secure token storage

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### AUTH-002: Role Model
**Summary**: Role model distinguishes internal roles, outside counsel, and landowner/portal users.

**Acceptance Criteria**:
- [ ] Internal roles: Admin, Legal, ROW, Finance
- [ ] Outside counsel role
- [ ] Landowner/portal user role
- [ ] Role-based access control enforcement

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### AUTH-003: Tokenized Landowner Access
**Summary**: Landowners access portal via tokenized, time-limited links.

**Acceptance Criteria**:
- [ ] Generate time-limited access tokens
- [ ] Token verification endpoint
- [ ] Token expiry enforcement
- [ ] Access logging

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

## EPIC 13: Audit & Security

**Description**: Application logs, audit trails, and file upload security.  
**Agreement Reference**: Exhibit A - "Technical Overview - Security & Audit"

### Stories

#### AUD-001: Audit Logging
**Summary**: Key operations are logged in application audit trails.

**Acceptance Criteria**:
- [ ] Log: creation/update of notices, ROEs, title/curative items, litigation events
- [ ] Log: offer/counteroffer creation and updates
- [ ] Log: landowner portal sessions and uploads
- [ ] Log: template changes and batch communications

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

#### AUD-002: File Upload Security
**Summary**: File uploads are validated and scanned per security protocols.

**Acceptance Criteria**:
- [ ] File type validation
- [ ] File size limits
- [ ] Security scanning (basic)
- [ ] Metadata logging

**Labels**: `milestone-2`, `scope-mvp`, `exhibit-a`, `backend`

---

## EPIC 14: Email Integration

**Description**: Integration with commercial email provider for communications.  
**Agreement Reference**: Exhibit A - "Technical Overview - Communications Integration"

### Stories

#### EMAIL-001: Email Provider Integration
**Summary**: System integrates with a commercial email provider for sending communications.

**Acceptance Criteria**:
- [ ] Integration with SendGrid, SES, or equivalent
- [ ] Send single emails
- [ ] Send batch emails
- [ ] Handle provider webhooks/APIs for delivery status

**Labels**: `milestone-4`, `scope-mvp`, `exhibit-a`, `backend`

---

#### EMAIL-002: Email Send Logging
**Summary**: Email send attempts and statuses are logged.

**Acceptance Criteria**:
- [ ] Log send attempt with timestamp
- [ ] Log delivery status (where provider allows)
- [ ] Link to communication record

**Labels**: `milestone-4`, `scope-mvp`, `exhibit-a`, `backend`

---

## EPIC 15: Milestone 1 - Technical Design

**Description**: Technical design, data model finalization, and backlog refinement.  
**Agreement Reference**: Exhibit B - "Milestone 1 – Technical Design & Backlog Refinement"

### Stories

#### M1-001: Data Model Finalization
**Summary**: Finalize data model and architecture for all MVP entities.

**Acceptance Criteria**:
- [ ] Data model for: Projects, Parcels, Notices, Service Attempts
- [ ] Data model for: ROEs, Litigation Cases and Deadlines
- [ ] Data model for: Title Documents, Curative Items, Appraisals
- [ ] Data model for: Payment & Negotiation objects (offers, counteroffers, statuses)
- [ ] Data model for: Communications and Audit logs
- [ ] Data model for: Documents and Templates
- [ ] Data model for: Alignments, Segments, Analytics aggregates
- [ ] Data model for: Landowner and outside-counsel access patterns

**Labels**: `milestone-1`, `scope-mvp`, `exhibit-b`, `design`

---

#### M1-002: User Journey Confirmation
**Summary**: Confirm user journeys and acceptance criteria for key features.

**Acceptance Criteria**:
- [ ] User journey: Landowner uploads and Negotiation Portal
- [ ] User journey: Template Generator
- [ ] User journey: Landowner Communications (one-to-many)
- [ ] User journey: Title & appraisal analytics, litigation packet views
- [ ] Acceptance criteria documented for each journey

**Labels**: `milestone-1`, `scope-mvp`, `exhibit-b`, `design`

---

#### M1-003: Backlog Refinement
**Summary**: Refine and prioritize functionality in agreed tooling (e.g., Jira).

**Acceptance Criteria**:
- [ ] All stories created in Jira
- [ ] Stories prioritized by milestone
- [ ] Acceptance criteria attached to stories
- [ ] Sprint planning ready

**Labels**: `milestone-1`, `scope-mvp`, `exhibit-b`, `design`

---

## EPIC 16: Milestone 5 - UAT & Hardening

**Description**: UAT support, defect remediation, and production-ready package.  
**Agreement Reference**: Exhibit B - "Milestone 5 – UAT Completion, Hardening & Production-Ready Package"

### Stories

#### M5-001: End-to-End UAT Support
**Summary**: Support UAT across representative end-to-end workflows.

**Acceptance Criteria**:
- [ ] UAT for: Project creation → parcel onboarding
- [ ] UAT for: Notices/service → ROE → title/curative
- [ ] UAT for: Negotiation → litigation tracking
- [ ] UAT for: Landowner portal use
- [ ] UAT defect tracking and triage

**Labels**: `milestone-5`, `scope-mvp`, `exhibit-b`, `uat`

---

#### M5-002: Defect Remediation
**Summary**: Remediate UAT defects above agreed severity thresholds.

**Acceptance Criteria**:
- [ ] Severity thresholds defined and agreed
- [ ] Critical/high severity defects resolved
- [ ] Defect resolution verified in UAT

**Labels**: `milestone-5`, `scope-mvp`, `exhibit-b`, `uat`

---

#### M5-003: Performance Tuning
**Summary**: Perform performance tuning based on UAT feedback.

**Acceptance Criteria**:
- [ ] Performance baseline established
- [ ] Key bottlenecks identified and addressed
- [ ] Load testing for expected concurrent users

**Labels**: `milestone-5`, `scope-mvp`, `exhibit-b`, `backend`, `frontend`

---

#### M5-004: Security Hardening
**Summary**: Perform security hardening based on UAT feedback.

**Acceptance Criteria**:
- [ ] Security review completed
- [ ] Identified vulnerabilities addressed
- [ ] Security documentation updated

**Labels**: `milestone-5`, `scope-mvp`, `exhibit-b`, `backend`

---

#### M5-005: Production-Ready Package
**Summary**: Deliver deployment-ready code, configuration, and documentation.

**Acceptance Criteria**:
- [ ] Deployment-ready code package
- [ ] API documentation
- [ ] Data model overview
- [ ] Migration scripts
- [ ] Configuration documentation

**Labels**: `milestone-5`, `scope-mvp`, `exhibit-b`, `backend`, `frontend`

---

## OUT OF SCOPE (MVP Exclusions)

**Agreement Reference**: Exhibit A - "Out-of-Scope Features (MVP)", Section 3.3

The following items are explicitly excluded from MVP scope and should NOT be scheduled:

### OOS-001: Valuation and Appraisal Computation
- Any valuation, appraisal, or compensation computations
- Independent appraisal models
- Automated determination of "fair market value"

**Labels**: `out-of-scope`, `exhibit-a`

---

### OOS-002: URA/HUD Compliance
- URA/HUD relocation benefit calculators
- Any URA/HUD compliance engines

**Labels**: `out-of-scope`, `exhibit-a`

---

### OOS-003: Environmental/NEPA Modules
- Full environmental compliance modules
- Full NEPA compliance modules

**Labels**: `out-of-scope`, `exhibit-a`

---

### OOS-004: Advanced Features
- Advanced deadline engines or automated rule libraries beyond Exhibit A specification
- Enterprise SSO
- Advanced BI

**Labels**: `out-of-scope`, `exhibit-a`

---

## Appendix: Story Count by Milestone

| Milestone | Epic Count | Story Count |
|-----------|------------|-------------|
| M1 | 1 | 3 |
| M2 | 12 | 32 |
| M3 | 8 | 12 |
| M4 | 6 | 15 |
| M5 | 1 | 5 |
| **Total** | **16** | **67** |

---

## Appendix: Agreement Cross-Reference

| Section | Description | Epics |
|---------|-------------|-------|
| 3.2(a) | Core project and parcel management | EPIC 1 |
| 3.2(b) | Legal-first notices & service engine | EPIC 2 |
| 3.2(c) | Right-of-Entry (ROE) management | EPIC 3 |
| 3.2(d) | Litigation calendar | EPIC 4 |
| 3.2(e) | Title & curative tracking | EPIC 5 |
| 3.2(f) | Payment ledger | EPIC 6 |
| 3.2(g) | Parcel communications and audit events | EPIC 8, 13 |
| 3.2(h) | GIS alignment and parcel segmentation | EPIC 10 |
| Exhibit A - Landowner Portal | Landowner access and uploads | EPIC 7 |
| Exhibit A - Documents & Templates | Template generator | EPIC 9 |
| Exhibit A - Analytics | Analytics & reporting | EPIC 11 |
| Exhibit A - Technical Overview | Auth, security, email | EPIC 12, 13, 14 |
| Exhibit B - M1 | Technical design | EPIC 15 |
| Exhibit B - M5 | UAT & hardening | EPIC 16 |
