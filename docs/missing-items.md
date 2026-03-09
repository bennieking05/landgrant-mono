# LandRight MVP - Missing Items & Gap Analysis

> Generated: January 2, 2026  
> Audit Scope: All backend endpoints and frontend pages

---

## Executive Summary

The LandRight MVP has **33 backend endpoints** across 18 route files and **4 frontend pages** with 11 components. Currently, **12 endpoints** are wired to frontend components, while **21 endpoints** are functional but lack UI integration.

---

## 1. Endpoints Without Frontend Integration

### 1.1 Health Probes (No UI Needed)

| Endpoint | Purpose | Notes |
|----------|---------|-------|
| `GET /health/live` | Kubernetes liveness probe | System infrastructure |
| `GET /health/invite` | Invite flow health check | System infrastructure |
| `GET /health/esign` | E-sign vendor health check | System infrastructure |

### 1.2 Cases

| Endpoint | Purpose | Missing UI Component |
|----------|---------|---------------------|
| `GET /cases/{parcel_id}` | Retrieve parcel details | Parcel detail view/modal |

### 1.3 Templates

| Endpoint | Purpose | Missing UI Component |
|----------|---------|---------------------|
| `GET /templates` | List available templates | Template browser |
| `POST /templates/render` | Render template with variables | Template preview panel |

### 1.4 AI Pipeline

| Endpoint | Purpose | Missing UI Component |
|----------|---------|---------------------|
| `POST /ai/drafts` | Generate AI-assisted draft | AI draft generation panel |

### 1.5 Workflows

| Endpoint | Purpose | Missing UI Component |
|----------|---------|---------------------|
| `POST /workflows/tasks` | Create workflow tasks | Task creation form |

### 1.6 Integrations (Webhook - No UI Needed)

| Endpoint | Purpose | Notes |
|----------|---------|-------|
| `POST /integrations/dockets` | Receive docket webhooks | External webhook receiver |

### 1.7 Portal

| Endpoint | Purpose | Missing UI Component |
|----------|---------|---------------------|
| `POST /portal/verify` | Verify magic link token | Token verification page/flow |

### 1.8 Notifications

| Endpoint | Purpose | Missing UI Component |
|----------|---------|---------------------|
| `POST /notifications/preview` | Preview/send notifications | Notification compose UI |

### 1.9 Parcels

| Endpoint | Purpose | Missing UI Component |
|----------|---------|---------------------|
| `GET /parcels` | List parcels with filters | Parcel list/table with filters |

### 1.10 Deadlines

| Endpoint | Purpose | Missing UI Component |
|----------|---------|---------------------|
| `GET /deadlines` | List project deadlines | Deadline list view |
| `POST /deadlines` | Create new deadline | Deadline creation form |
| `GET /deadlines/ical` | Export deadlines as iCal | iCal download button |

### 1.11 Title

| Endpoint | Purpose | Missing UI Component |
|----------|---------|---------------------|
| `GET /title/instruments` | List title instruments | Title documents panel |
| `POST /title/instruments` | Upload title instrument | Title upload form |

### 1.12 Appraisals

| Endpoint | Purpose | Missing UI Component |
|----------|---------|---------------------|
| `GET /appraisals` | Get parcel appraisal | Appraisal display panel |
| `POST /appraisals` | Create/update appraisal | Appraisal edit form |

### 1.13 Ops

| Endpoint | Purpose | Missing UI Component |
|----------|---------|---------------------|
| `GET /ops/routes/plan` | Get route optimization plan | Route planning display/export |

### 1.14 Outside Counsel

| Endpoint | Purpose | Missing UI Component |
|----------|---------|---------------------|
| `GET /outside/repository/completeness` | Check repository readiness | Completeness checklist panel |
| `POST /outside/case/initiate` | Initiate outside counsel case | Case initiation form |
| `POST /outside/status` | Update case status | Status update form |

---

## 2. Missing Synthetic/Test Data

### 2.1 Required for Full Testing

| Entity | Current State | Required |
|--------|---------------|----------|
| Projects | 1 (PRJ-001) | 2+ (add PRJ-002 for multi-project testing) |
| Parcels | 1 (PARCEL-001) | 5+ (varied risk scores and deadlines) |
| Title Instruments | 0 | 2+ for PARCEL-001 |
| Appraisals | 0 | 1 for PARCEL-001 with summary |
| Deadlines | 0 | 3+ for PRJ-001 with varied due dates |
| Communications | 1 (email) | 3+ (add SMS, certified mail) |
| Rule Results | 1 | 2+ (varied rules) |

### 2.2 Data Dependencies

```
PRJ-001 (Project)
├── PARCEL-001 (Parcel)
│   ├── TitleInstrument x2
│   ├── Appraisal x1
│   ├── Communication x3
│   └── RuleResult x2
├── PARCEL-002 through PARCEL-005 (Parcels)
├── Deadline x3
└── Budget x1
```

---

## 3. Frontend Components Needed

### 3.1 New Components

| Component | Page Target | Endpoints Used |
|-----------|-------------|----------------|
| `ParcelList.tsx` | WorkbenchPage | `GET /parcels` |
| `DeadlineManager.tsx` | CounselPage | `GET /deadlines`, `POST /deadlines` |
| `TitlePanel.tsx` | WorkbenchPage | `GET /title/instruments`, `POST /title/instruments` |
| `AppraisalPanel.tsx` | WorkbenchPage | `GET /appraisals`, `POST /appraisals` |
| `TemplateViewer.tsx` | CounselPage | `GET /templates`, `POST /templates/render` |
| `AIDraftPanel.tsx` | IntakePage | `POST /ai/drafts` |
| `OutsideCounselPanel.tsx` | CounselPage | `GET /outside/repository/completeness`, `POST /outside/case/initiate` |

### 3.2 Page Updates Required

| Page | Current Components | Add Components |
|------|-------------------|----------------|
| IntakePage | InviteCard, ParcelMapPlaceholder, UploadPanel, DecisionActions, IntakeForm | AIDraftPanel |
| WorkbenchPage | ParcelMapPlaceholder, CommsLog, PacketChecklist, RuleResults | ParcelList, TitlePanel, AppraisalPanel |
| CounselPage | CounselQueue, BudgetPanel, BinderStatus | DeadlineManager, TemplateViewer, OutsideCounselPanel |

---

## 4. API Client Gaps

### 4.1 Current State

The `frontend/src/lib/api.ts` exports:
- `apiGet<T>()` - Generic GET
- `apiPostJson<T>()` - Generic JSON POST
- `apiPostForm<T>()` - Generic FormData POST
- `createCase()` - Typed wrapper for case creation

### 4.2 Missing Typed Wrappers

All endpoints should have typed wrapper functions for:
- Type safety
- Autocomplete support
- Centralized error handling
- Easier mocking in tests

---

## 5. Integration Testing Gaps

### 5.1 Missing E2E Flows

| Flow | Status |
|------|--------|
| Landowner complete journey (invite → verify → upload → decision) | Partial (no verify step) |
| Agent parcel management (list → filter → view details) | Missing list/filter |
| Counsel approval workflow (templates → approval → binder export) | Missing template browser |
| Outside counsel handoff (completeness check → initiate → status updates) | Completely missing |

### 5.2 Missing RBAC Test Coverage

| Persona | Tested Resources | Untested Resources |
|---------|------------------|-------------------|
| landowner | portal, decision | - |
| land_agent | parcel, communication, packet | title, appraisal, ops |
| in_house_counsel | template, binder, budget, deadline | - |
| outside_counsel | - | case, deadline, status |
| admin | - | rbac, audit |

---

## 6. External Integration Stubs

### 6.1 Vendor Integrations Not Connected

| Vendor | Purpose | Current State |
|--------|---------|---------------|
| SendGrid | Email delivery | Stub in notifications.py |
| Twilio | SMS delivery | Stub in notifications.py |
| Adobe Sign | E-signatures | Health probe only |
| Lob | Certified mail | Health probe only |
| ArcGIS | Map rendering | Placeholder component |

---

## 7. Priority Matrix

### 7.1 Must Have (P0)

- [ ] Synthetic data for all entities
- [ ] Parcel list with filtering
- [ ] Title/Appraisal document management
- [ ] Deadline management

### 7.2 Should Have (P1)

- [ ] Template browser and preview
- [ ] AI draft generation UI
- [ ] Outside counsel handoff flow

### 7.3 Nice to Have (P2)

- [ ] Route planning visualization
- [ ] iCal export integration
- [ ] Full notification compose UI

---

## 8. Action Items

1. **Expand seed data** - Add comprehensive test entities in `main.py` and `seed_data.py`
2. **Add API wrappers** - Create typed functions in `api.ts` for all endpoints
3. **Build ParcelList** - Filterable table using `GET /parcels`
4. **Build DeadlineManager** - CRUD for deadlines
5. **Build TitlePanel** - Upload and list title instruments
6. **Build AppraisalPanel** - View and edit appraisal data
7. **Build TemplateViewer** - Browse and preview templates
8. **Build AIDraftPanel** - Generate AI drafts
9. **Build OutsideCounselPanel** - Handoff workflow
10. **Update page layouts** - Integrate new components into pages

