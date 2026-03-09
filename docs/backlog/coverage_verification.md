# Backlog Coverage Verification

> Generated: January 24, 2026  
> Verified against: Software Development Agreement (Effective Date: January 5, 2026)

---

## Coverage Summary

| Category | Items in Agreement | Items in Backlog | Status |
|----------|-------------------|------------------|--------|
| Epics | 16 | 17 (incl. Out-of-Scope) | Complete |
| Stories | ~67 | 72 | Complete |
| Milestones | 5 | 5 | Complete |
| Out-of-Scope Items | 4 | 4 | Complete |

---

## Section 3.2 MVP Scope Coverage

| Section | Agreement Requirement | Epic | Stories | Status |
|---------|----------------------|------|---------|--------|
| 3.2(a) | Core project and parcel management | EPIC 1: Projects & Parcels | PP-001, PP-002, PP-003 | Covered |
| 3.2(b) | Legal-first notices & service engine | EPIC 2: Notices & Service | NS-001 to NS-004 | Covered |
| 3.2(c) | Right-of-Entry (ROE) management | EPIC 3: ROE Management | ROE-001 to ROE-004 | Covered |
| 3.2(d) | Litigation calendar | EPIC 4: Litigation & Case Deadline | LIT-001 to LIT-005 | Covered |
| 3.2(e) | Title & curative tracking | EPIC 5: Title & Curative | TIT-001 to TIT-005 | Covered |
| 3.2(f) | Payment ledger | EPIC 6: Payment & Negotiation | PAY-001 to PAY-004 | Covered |
| 3.2(g) | Parcel communications and audit events | EPIC 8, EPIC 13 | COM-001 to COM-005, AUD-001 to AUD-002 | Covered |
| 3.2(h) | GIS alignment and parcel segmentation | EPIC 10: GIS Alignment | GIS-001 to GIS-004 | Covered |

---

## Exhibit A Functional Requirements Coverage

| Requirement | Epic | Status |
|-------------|------|--------|
| Projects and Parcels Functionality | EPIC 1 | Covered |
| Legal Playbooks – Notices & Service Functionality | EPIC 2 | Covered |
| Right-of-Entry (ROE) Manager Functionality | EPIC 3 | Covered |
| Litigation & Case Deadline Calendar Functionality | EPIC 4 | Covered |
| Title & Curative Tracker + Title Report Analytics | EPIC 5 | Covered |
| Payment & Negotiation Module (Negotiation Portal) | EPIC 6 | Covered |
| Landowner Portal: Status and Uploads | EPIC 7 | Covered |
| Communications & Landowner Communications (One-to-Many) | EPIC 8 | Covered |
| Document Management & Template Generator | EPIC 9 | Covered |
| GIS Alignment & Parcel Segmentation Functionality | EPIC 10 | Covered |
| Analytics & Reporting (Including Title/Appraisal Analytics) | EPIC 11 | Covered |

---

## Exhibit A Technical Overview Coverage

| Technical Requirement | Epic | Status |
|----------------------|------|--------|
| Authentication & Authorization (JWT, roles, tokens) | EPIC 12 | Covered |
| Security & Audit (logging, file security) | EPIC 13 | Covered |
| Communications Integration (email provider) | EPIC 14 | Covered |
| Template & Document Generation | EPIC 9 | Covered |
| Analytics queries and visualization | EPIC 11 | Covered |
| PostGIS geometry support | EPIC 1, EPIC 10 | Covered |
| S3-compatible storage | EPIC 9 | Covered |

---

## Exhibit B Milestone Coverage

| Milestone | Target | Epic | Stories | Status |
|-----------|--------|------|---------|--------|
| M1 - Technical Design & Backlog Refinement | 30 days | EPIC 15 | M1-001 to M1-003 | Covered |
| M2 - Backend MVP API | 60 days | Multiple | 32 stories | Covered |
| M3 - Frontend Internal Web App | 90 days | Multiple | 12 stories | Covered |
| M4 - Landowner Portal, Negotiation Portal & Comms | 120 days | Multiple | 15 stories | Covered |
| M5 - UAT Completion, Hardening & Production-Ready | 160 days | EPIC 16 | M5-001 to M5-005 | Covered |

---

## Exhibit A Out-of-Scope Coverage

| Exclusion | Documented | Status |
|-----------|------------|--------|
| Valuation, appraisal, or compensation computations | OOS-001 | Marked |
| URA/HUD relocation benefit calculators | OOS-002 | Marked |
| Full environmental and NEPA compliance modules | OOS-003 | Marked |
| Advanced deadline engines, Enterprise SSO, Advanced BI | OOS-004 | Marked |

---

## User Journey Coverage (Exhibit B - Milestone 1 Deliverables)

| User Journey | Stories | Status |
|--------------|---------|--------|
| Landowner uploads and Negotiation Portal | LP-001 to LP-006, PAY-001 to PAY-004 | Covered |
| Template Generator | DOC-002 to DOC-007 | Covered |
| Landowner Communications (one-to-many) | COM-002, COM-003, COM-005 | Covered |
| Title & appraisal analytics | TIT-003, TIT-005, ANA-002, ANA-004 | Covered |
| Litigation packet views | LIT-004, LIT-005 | Covered |

---

## Representative Journeys from Agreement

| Journey | Agreement Reference | Epic | Status |
|---------|---------------------|------|--------|
| Set up a new ED/LA project | Exhibit A - Projects and Parcels | EPIC 1 | Covered |
| Record a statutory notice and service attempt | Exhibit A - Notices & Service | EPIC 2 | Covered |
| Offer Letters workflow | Exhibit A - Payment & Negotiation | EPIC 6, EPIC 7 | Covered |

---

## Verification Result

**All requirements from the Software Development Agreement are covered in the backlog.**

- 17 Epics (including Out-of-Scope tracking)
- 72 Stories with acceptance criteria
- All 5 milestones mapped
- All exclusions documented
- Cross-references to agreement sections included

### Files Generated

1. `/docs/backlog/landright_backlog.md` - Full Markdown backlog with acceptance criteria
2. `/docs/backlog/landright_backlog.csv` - Jira-importable CSV format
3. `/docs/backlog/coverage_verification.md` - This verification document
