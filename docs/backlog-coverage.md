# Backlog Coverage Map (EminentAI_Backlog.csv)

This doc maps each backlog story to concrete code locations and defines **pass/fail checks** for local verification.

Legend:
- **Implemented**: backed by DB/services; deterministic; not a demo stub
- **Partial**: UI wired + API exists, but incomplete semantics/side-effects
- **Stubbed**: placeholder response and/or in-memory fallback that does not meet acceptance criteria
- **Missing**: no route/service/UI yet

## EPIC A — Landowner Portal

### Magic-link invite & one-time verification
- **Code**:
  - API: [`backend/app/api/routes/portal.py`](../backend/app/api/routes/portal.py) (`POST /portal/invites`) — currently returns an ID + expiry only
  - UI: [`frontend/components/InviteCard.tsx`](../frontend/components/InviteCard.tsx)
- **Current status**: **Stubbed**
- **Pass/fail checks**:
  - Invite links **expire** and cannot be reused
  - Verification is **logged** (audit trail)
  - Failed attempts are **rate-limited**
  - Notification payload can be **previewed** (email/SMS) even if not sent

### Parcel & timeline overview
- **Code**:
  - API: [`backend/app/api/routes/cases.py`](../backend/app/api/routes/cases.py) (`GET /cases/{parcel_id}`)
  - UI: [`frontend/app/intake/page.tsx`](../frontend/app/intake/page.tsx), [`frontend/components/ParcelMapPlaceholder.tsx`](../frontend/components/ParcelMapPlaceholder.tsx)
- **Current status**: **Partial** (parcel snapshot exists; map is placeholder)
- **Pass/fail checks**:
  - Parcel overview renders details + key dates/timeline
  - Load budget measurable (target: <2s on 4G) with at least basic perf instrumentation

### Document review (offer, appraisal)
- **Code**:
  - Models: [`backend/app/db/models.py`](../backend/app/db/models.py) (`Document`)
  - Templates: [`templates/library/`](../templates/library/)
  - API: [`backend/app/api/routes/templates.py`](../backend/app/api/routes/templates.py) (`GET /templates`, `POST /templates/render`)
- **Current status**: **Partial** (template render is naive string replace; no PDF viewer/versioned document retrieval)
- **Pass/fail checks**:
  - PDF viewer renders offer/appraisal documents
  - Documents are **version-stamped**
  - Hash recorded in **audit/evidence log**

### Chat & uploads (POA, W-9, photos)
- **Code**:
  - API: [`backend/app/api/routes/portal.py`](../backend/app/api/routes/portal.py) (`GET/POST /portal/uploads`) — currently stores upload metadata in-memory only
  - UI: [`frontend/components/UploadPanel.tsx`](../frontend/components/UploadPanel.tsx)
  - Models: [`backend/app/db/models.py`](../backend/app/db/models.py) (`Document`, `Communication`)
- **Current status**: **Stubbed**
- **Pass/fail checks**:
  - Upload limit enforced (≤ 50MB)
  - Virus scan status recorded (can be mocked locally, but must be tracked)
  - Threaded chat exists and is exportable to binder timeline
  - Uploads are stored as versioned `Document` with sha256 + storage_path (local)

### Decision actions: Accept / Counter / Request Call
- **Code**:
  - API: [`backend/app/api/routes/portal.py`](../backend/app/api/routes/portal.py) (`POST /portal/decision`) — currently in-memory only
  - UI: [`frontend/components/DecisionActions.tsx`](../frontend/components/DecisionActions.tsx)
  - Workflows: [`backend/app/api/routes/workflows.py`](../backend/app/api/routes/workflows.py) (`POST /workflows/tasks`)
- **Current status**: **Stubbed**
- **Pass/fail checks**:
  - Decision creates workflow task(s) (and counter routes to agent queue)
  - SLA timer visible and persisted
  - Audit event captured with actor persona and payload hash

### E-sign & confirmation
- **Code**:
  - Health probe exists: [`backend/app/api/routes/health.py`](../backend/app/api/routes/health.py) (`GET /health/esign`)
  - Integrations stubs: (to be implemented) e-sign webhook/verification
- **Current status**: **Missing/Stubbed**
- **Pass/fail checks**:
  - Signer identity + timestamps persisted
  - Confirmation email/SMS is generated and stored (preview mode acceptable without secrets)

## EPIC B — Agent Workbench

### Parcel list with filters & map view
- **Code**:
  - UI: [`frontend/app/workbench/page.tsx`](../frontend/app/workbench/page.tsx), [`frontend/components/ParcelMapPlaceholder.tsx`](../frontend/components/ParcelMapPlaceholder.tsx)
  - API: (missing) list parcels with filters/pagination
- **Current status**: **Missing/Partial**
- **Pass/fail checks**:
  - Filter by stage/risk/deadline with API-backed pagination
  - Map can render large sets (local perf harness for 1k)

### Routing & field planning
- **Current status**: **Missing**
- **Pass/fail checks**:
  - Export routes to mobile; daily plan PDF/CSV

### Title analytics (owners/lienholders)
- **Code**:
  - Models exist: [`backend/app/db/models.py`](../backend/app/db/models.py) (`TitleInstrument`)
  - Pipeline placeholder: [`backend/app/services/ai_pipeline.py`](../backend/app/services/ai_pipeline.py)
- **Current status**: **Missing/Stubbed**
- **Pass/fail checks**:
  - OCR + parse title docs; confidence score; export CSV

### Appraisal analytics & comps
- **Code**:
  - Models exist: [`backend/app/db/models.py`](../backend/app/db/models.py) (`Appraisal`)
- **Current status**: **Missing**
- **Pass/fail checks**:
  - Attach comps; summary stats; links to source docs

### Comms log (batch & 1:1)
- **Code**:
  - API: [`backend/app/api/routes/communications.py`](../backend/app/api/routes/communications.py) (`GET /communications`)
  - UI: [`frontend/components/CommsLog.tsx`](../frontend/components/CommsLog.tsx)
  - Model: `Communication` in [`backend/app/db/models.py`](../backend/app/db/models.py)
- **Current status**: **Partial** (API has stub fallback; no send/preview endpoints)
- **Pass/fail checks**:
  - Entries include delivery proof + SLA timers
  - Outbox/preview mode for email/SMS when secrets absent

### Pre-offer packet generation
- **Code**:
  - API: [`backend/app/api/routes/packet.py`](../backend/app/api/routes/packet.py) (`GET /packet/checklist`)
  - UI: [`frontend/components/PacketChecklist.tsx`](../frontend/components/PacketChecklist.tsx)
- **Current status**: **Stubbed**
- **Pass/fail checks**:
  - Checklist computed from actual docs uploaded/attached
  - Cannot complete until required docs present; server-enforced

### Dispatch to portal & tracking
- **Current status**: **Missing**
- **Pass/fail checks**:
  - Opens/receipts stored; follow-up scheduler; escalations

## EPIC C — Counsel Controls

### Legal review trigger engine
- **Code**:
  - Rules: [`backend/app/services/rules_engine.py`](../backend/app/services/rules_engine.py)
  - API list: [`backend/app/api/routes/rules.py`](../backend/app/api/routes/rules.py)
  - Tests: [`backend/tests/test_rules_engine.py`](../backend/tests/test_rules_engine.py)
- **Current status**: **Partial** (rules eval exists; task creation/gating not implemented end-to-end)
- **Pass/fail checks**:
  - Rules create legal tasks with deterministic citations and evidence hooks

### Template generator (IOL/FOL/easements)
- **Code**:
  - Template library: [`templates/library/`](../templates/library/)
  - API list/render: [`backend/app/api/routes/templates.py`](../backend/app/api/routes/templates.py)
  - UI: (minimal) counsel view scaffolding
- **Current status**: **Partial**
- **Pass/fail checks**:
  - Clauses versioned; variables resolve; approval workflow enforced by persona/RBAC

### Good-faith binder & service proof
- **Code**:
  - UI: [`frontend/components/BinderStatus.tsx`](../frontend/components/BinderStatus.tsx)
  - API: [`backend/app/api/routes/binder.py`](../backend/app/api/routes/binder.py) (status stub), [`backend/app/api/routes/workflows.py`](../backend/app/api/routes/workflows.py) (export stub)
  - Test: [`backend/tests/test_workflows.py`](../backend/tests/test_workflows.py)
  - Spec: [`docs/evidence.md`](./evidence.md)
- **Current status**: **Stubbed**
- **Pass/fail checks**:
  - Export produces PDF+JSON bundle (local filesystem OK) with immutable hash persisted and audit event

### Litigation packet export
- **Current status**: **Missing**
- **Pass/fail checks**:
  - Paginates contacts/title/appraisal/FOL; download zip

### Budget/utilization tracking
- **Code**:
  - API: [`backend/app/api/routes/budgets.py`](../backend/app/api/routes/budgets.py)
  - UI: [`frontend/components/BudgetPanel.tsx`](../frontend/components/BudgetPanel.tsx)
  - Model: `Budget` in [`backend/app/db/models.py`](../backend/app/db/models.py)
- **Current status**: **Partial** (DB-backed but returns stub fallback; no 80/100 alerts)
- **Pass/fail checks**:
  - Alerts fire at 80%/100% and persist/audit

## EPIC D — Outside Counsel

### Repository access & completeness check
- **Current status**: **Missing**
- **Pass/fail checks**:
  - Permissions enforced; checklist 100% before filing

### Case initiation from approved templates
- **Current status**: **Missing**
- **Pass/fail checks**:
  - Auto-fill party data; docket placeholder; draft saved

### Client approvals & status updates
- **Current status**: **Missing**
- **Pass/fail checks**:
  - Two-way approvals; immutable audit; status reasons

### Deadline calendar & alerts
- **Current status**: **Missing**
- **Pass/fail checks**:
  - iCal subscribe; 14/7/1 day alerts; timezone-aware

### Budget estimate & variance reporting
- **Current status**: **Missing/Partial**
- **Pass/fail checks**:
  - Estimate; monthly actuals; variance explanation field

## Cross-Cutting

### RBAC
- **Code**:
  - RBAC matrix: [`docs/rbac.md`](./rbac.md)
  - Enforcement: [`backend/app/security/rbac.py`](../backend/app/security/rbac.py)
  - Persona propagation: [`frontend/lib/api.ts`](../frontend/lib/api.ts) (`X-Persona`)
- **Current status**: **Partial** (matrix exists, but many resources missing; no row-level scoping yet)
- **Pass/fail checks**:
  - Least privilege; negative tests for persona/resource/action combos

### Audit logging & evidence hashing
- **Code**:
  - Models: `AuditEvent`, `Document`, `Communication` in [`backend/app/db/models.py`](../backend/app/db/models.py)
  - Spec: [`docs/evidence.md`](./evidence.md)
- **Current status**: **Missing/Partial**
- **Pass/fail checks**:
  - Who/what/when; cryptographic hash per sensitive action/export; immutable append-only semantics locally

### Notifications (Email/SMS)
- **Current status**: **Missing**
- **Pass/fail checks**:
  - Provider wiring behind flags; preview/outbox mode when secrets absent; retries + delivery proofs when enabled

### Accessibility & localization
- **Code**:
  - Locale scaffolding: [`templates/i18n/en-US.json`](../templates/i18n/en-US.json)
  - Frontend scaffolding: Next.js + Tailwind in [`frontend/app/`](../frontend/app/)
- **Current status**: **Partial**
- **Pass/fail checks**:
  - WCAG 2.1 AA basics; language toggle plumbing; RTL readiness (layout/css patterns)

### SOC 2 control implementation
- **Current status**: **Doc-driven / Partial**
- **Pass/fail checks**:
  - Evidence store hooks; access/change mgmt references; incident runbooks exist under [`docs/runbooks/`](./runbooks/)



