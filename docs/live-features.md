# Live Features Checklist

This document maps the Software Development Agreement scope items to the current implementation status. All items marked "Live" are reachable in the UI and operational.

Last updated: January 2026

---

## Agreement Section 3.2 - MVP Scope

### (a) Core Project & Parcel Management
| Feature | Status | Backend | Frontend |
|---------|--------|---------|----------|
| Projects with jurisdiction | Live | `Project` model, `/cases` | IntakeForm |
| Parcels with PostGIS geometry | Live | `Parcel` model with `geom` field, `/parcels` | ParcelList, WorkbenchPage |
| Party management | Live | `Party`, `ParcelParty` models | IntakeForm |

### (b) Legal-First Notices & Service Engine
| Feature | Status | Backend | Frontend |
|---------|--------|---------|----------|
| Notice tracking | Live | `Communication` model | CommsLog |
| Service attempts & status | Live | `delivery_status`, `delivery_proof` fields | CommsLog |
| Per-jurisdiction rule validation | Live | `rules_engine.py`, `/rules/results` | RuleResults |
| Indiana statutory deadlines | Live | `rules/in.yaml`, `/deadlines/derive` | DeadlineManager |

### (c) Right-of-Entry (ROE) Management
| Feature | Status | Backend | Frontend |
|---------|--------|---------|----------|
| ROE templates | Partial | Template system supports ROE docs | TemplateViewer |
| Effective/expire dates | Via metadata | `Document.metadata_json` | - |
| Field check-in/out | Future | - | - |

### (d) Litigation Calendar
| Feature | Status | Backend | Frontend |
|---------|--------|---------|----------|
| Deadlines with parcel/project scope | Live | `Deadline` model, `/deadlines` | DeadlineManager |
| Manual event creation | Live | `POST /deadlines` | DeadlineManager |
| iCal export | Live | `GET /deadlines/ical` | DeadlineManager |
| Statutory deadline derivation | Live | `POST /deadlines/derive` | DeadlineManager |

### (e) Title & Curative Tracking
| Feature | Status | Backend | Frontend |
|---------|--------|---------|----------|
| Title document metadata | Live | `TitleInstrument` model | TitlePanel |
| Document upload | Live | `POST /title/instruments` | TitlePanel |
| OCR payload storage | Live | `ocr_payload` field | TitlePanel |
| Curative item status | Via metadata | `metadata_json` field | TitlePanel |

### (f) Payment Ledger
| Feature | Status | Backend | Frontend |
|---------|--------|---------|----------|
| Budget tracking (cap/actual) | Live | `Budget` model, `/budgets/summary` | BudgetPanel |
| Payment status (status-only) | Live | `StatusChange` model | BudgetPanel |
| No valuation/dollar amounts | Compliant | Per agreement exclusion | - |

### (g) Parcel Communications & Audit Events
| Feature | Status | Backend | Frontend |
|---------|--------|---------|----------|
| Multi-channel communications | Live | `Communication` model (email, sms, mail) | CommsLog |
| Delivery proof tracking | Live | `delivery_proof` JSON field | CommsLog |
| Audit events | Live | `AuditEvent` model | - |
| Hash-based integrity | Live | `hash` field on audit entries | - |

### (h) GIS Alignment & Parcel Segmentation
| Feature | Status | Backend | Frontend |
|---------|--------|---------|----------|
| Parcel geometry storage | Live | `Parcel.geom` JSON field | ParcelMapPlaceholder |
| Alignment import | Future | - | - |
| Segment generation | Future | - | - |

---

## Milestone 2 - Backend MVP API

| Component | Status | Implementation |
|-----------|--------|----------------|
| Core domain models | Live | `backend/app/db/models.py` |
| REST APIs for all entities | Live | `backend/app/api/routes/` |
| S3-compatible storage | Live | `Document.storage_path`, local_storage |
| JWT-based auth | Live | `X-Persona` header, RBAC |
| Role model (5 personas) | Live | `Persona` enum |
| Audit logging | Live | `AuditEvent` model |
| Notice & service tracking | Live | `Communication` model |
| Litigation deadlines | Live | `Deadline` model |
| Title instruments | Live | `TitleInstrument` model |
| Template storage | Live | `templates/library/` |
| Template generation | Live | `/templates/render` |
| Landowner uploads | Live | `/portal/uploads` |
| Analytics queries | Live | `/budgets/summary`, `/ops/routes/plan` |

---

## Milestone 3 - Frontend Internal Web App

| View | Status | Route | Components |
|------|--------|-------|------------|
| Project/parcel lists | Live | `/workbench` | ParcelList |
| Notices & Service | Live | `/workbench` | CommsLog |
| Litigation & Deadlines | Live | `/counsel` | DeadlineManager |
| Title & Curative | Live | `/workbench` | TitlePanel |
| Communications & Audit | Live | `/workbench` | CommsLog |
| Documents & Templates | Live | `/counsel` | TemplateViewer |
| Parcel map | Placeholder | `/workbench` | ParcelMapPlaceholder |
| Template management | Live | `/counsel` | TemplateViewer |
| Analytics/reporting | Live | `/ops` | RoutePlanPanel |

---

## Milestone 4 - Landowner Portal & Communications

| Feature | Status | Route | Components |
|---------|--------|-------|------------|
| Token-based portal access | Live | `/intake` | InviteCard |
| Document list & uploads | Live | `/intake` | UploadPanel |
| Decision actions (Accept/Counter/Call) | Live | `/intake` | DecisionActions |
| Batch communications UI | Live | `/ops` | NotificationsPanel |
| Template generator | Live | `/counsel` | TemplateViewer |
| Deadline calendar | Live | `/counsel` | DeadlineManager |

---

## Agreement Exclusions (Section 3.3)

The following are **out of scope** per the agreement:
- Valuation, appraisal, or compensation computations
- URA/HUD relocation benefit calculators
- Full environmental and NEPA compliance modules
- Advanced deadline engines beyond statutory rules

---

## Live API Endpoints

### Health
- `GET /health/live` - Liveness probe
- `GET /health/invite` - Portal invite system check
- `GET /health/esign` - E-sign vendor check

### Cases & Parcels
- `POST /cases` - Create case with parcels
- `GET /cases/{parcel_id}` - Get case details
- `GET /parcels` - List/filter parcels

### Templates
- `GET /templates` - List available templates
- `POST /templates/render` - Render template with variables

### Deadlines
- `GET /deadlines` - List deadlines by project
- `POST /deadlines` - Create deadline
- `POST /deadlines/derive` - Derive statutory deadlines
- `GET /deadlines/ical` - Export iCal feed

### Communications
- `GET /communications` - List by parcel
- `POST /notifications/preview` - Preview notification

### Portal
- `POST /portal/invites` - Send invite
- `POST /portal/verify` - Verify token
- `GET /portal/decision/options` - Get decision options
- `POST /portal/decision` - Submit decision
- `GET /portal/uploads` - List uploads
- `POST /portal/uploads` - Upload file

### Workflows
- `POST /workflows/tasks` - Create task
- `GET /workflows/approvals` - List approvals
- `POST /workflows/binder/export` - Export binder

### Title & Appraisals
- `GET /title/instruments` - List by parcel
- `POST /title/instruments` - Upload instrument
- `GET /appraisals` - Get by parcel
- `POST /appraisals` - Upsert appraisal

### Operations
- `GET /ops/routes/plan` - Generate route plan

### Budgets & Binder
- `GET /budgets/summary` - Get budget summary
- `GET /binder/status` - Get binder status

### Rules
- `GET /rules/results` - List fired rules by parcel

### Integrations
- `POST /integrations/dockets` - Docket webhook receiver

### Outside Counsel
- `GET /outside/repository/completeness` - Check repo completeness
- `POST /outside/case/initiate` - Initiate outside case
- `POST /outside/status` - Update status

---

## Frontend Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | HomePage | Landing with workspace cards |
| `/intake` | IntakePage | Landowner portal flows |
| `/workbench` | WorkbenchPage | Agent parcel management |
| `/counsel` | CounselPage | Counsel controls & templates |
| `/ops` | OpsPage | Operations & integrations |

---

## Templates Available

| Template ID | Jurisdiction | Description |
|-------------|--------------|-------------|
| `fol` | TX | Final Offer Letter (Texas) |
| `in_offer` | IN | Uniform Property/Easement Acquisition Offer (Indiana) |

---

## Rules Packs

| Jurisdiction | File | Deadlines |
|--------------|------|-----------|
| Texas (TX) | `rules/tx.yaml` | Valuation threshold, good faith meeting |
| Indiana (IN) | `rules/in.yaml` | Full statutory chain (IC 32-24) |
