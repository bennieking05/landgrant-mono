# LandRight AI-First Modules

> Implementation guide for AI-first functionality in the LandRight eminent domain platform.

## Overview

This document describes the AI-first modules that provide audit-grade evidence, human-in-the-loop controls, and multi-state requirement management for the LandRight platform.

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI-First Architecture                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ Requirements    │  │ Citation &      │  │ AI Telemetry    │             │
│  │ Ops (Module A)  │  │ Provenance (B)  │  │ (Module C)      │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
│           │                    │                    │                       │
│           └────────────────────┼────────────────────┘                       │
│                               │                                             │
│  ┌─────────────────┐  ┌──────┴────────┐  ┌─────────────────┐               │
│  │ Document QA     │  │ Approval      │  │ State Summary   │               │
│  │ (Module D)      │  │ Workflow (E)  │  │ (Module I)      │               │
│  └─────────────────┘  └───────────────┘  └─────────────────┘               │
│                                                                              │
│                    ┌─────────────────────┐                                  │
│                    │ Evaluation Harness  │                                  │
│                    │ (Module H)          │                                  │
│                    └─────────────────────┘                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Modules

### A. Requirements Operations (`/rules/*` endpoints)

**Purpose**: 50-state statutory and case law requirement management.

**Key Features**:
- State pack import and validation
- Version management with diffing
- Canonical requirement normalization
- Regulatory update monitoring (stub)

**API Endpoints**:
```
POST /rules/import_state_pack     Import YAML pack
POST /rules/validate_pack         Validate before publish
GET  /rules/state/{state}/diff    Compare versions
POST /rules/publish               Publish to active
GET  /rules/state/{state}         Get active pack
GET  /rules/jurisdictions         List all states
GET  /rules/requirements/{state}  Get normalized requirements
```

**Service**: `backend/app/services/requirements_ops.py`

### B. Evidence-Grade Citation & Provenance (`/audit/*` endpoints)

**Purpose**: Link every AI output to authoritative sources.

**Key Features**:
- Source ingestion with content hashing
- Citation linking to AI outputs
- Claim verification
- Source verification workflow

**API Endpoints**:
```
POST /audit/sources               Create source
GET  /audit/sources               Search sources
POST /audit/sources/{id}/verify   Verify source
GET  /audit/citations/{type}/{id} Get entity citations
POST /audit/citations/verify      Verify AI output citations
```

**Database Tables**:
- `sources`: Authoritative legal sources
- `citations`: Links between claims and sources

**Service**: `backend/app/services/citations.py`

### C. AI Telemetry & Decision Trace (`/audit/ai-events/*` endpoints)

**Purpose**: Complete audit trail for AI operations.

**Key Features**:
- Full input/output logging with hashing
- Reproducible run capability
- Cost tracking per model/action
- Prompt template versioning

**API Endpoints**:
```
GET  /audit/ai-events             List AI events
GET  /audit/ai-events/{id}        Full event trace
GET  /audit/ai-events/{id}/replay Get replay config
GET  /audit/costs                 Cost summary
```

**Database Tables**:
- `ai_events`: All AI calls with full context
- `prompt_templates`: Versioned prompts

**Service**: `backend/app/services/ai_telemetry.py`

### D. Document QA & Risk Scoring (`/qa/*` endpoints)

**Purpose**: Pre-send/pre-file quality validation.

**Key Features**:
- Required clause checking (per state)
- Forbidden language detection
- Name/date/amount consistency
- Risk scoring (red/yellow/green)

**API Endpoints**:
```
POST /qa/check                    Run QA checks
GET  /qa/reports/{id}             Get full report
GET  /qa/reports/{id}/checks      Get check details
GET  /qa/reports                  List reports
POST /qa/risk-score               Calculate risk score
POST /qa/validate-for-send        Pre-send validation
GET  /qa/required-clauses/{state} Get required clauses
```

**Database Tables**:
- `qa_reports`: QA check results
- `qa_checks`: Individual check results

**Service**: `backend/app/services/qa_checks.py`

### E. Human-in-Loop Approval Workflow (`/approvals/*` endpoints)

**Purpose**: Ensure human approval before irreversible actions.

**Key Features**:
- Status workflow: draft → qa_passed → pending_review → approved → sent/filed
- Content hash verification
- Full audit trail
- Approval gating

**API Endpoints**:
```
POST /approvals/request           Request approval
GET  /approvals                   List approvals
GET  /approvals/{id}              Get approval details
POST /approvals/{id}/approve      Approve action
POST /approvals/{id}/reject       Reject action
POST /approvals/{id}/assign       Assign reviewer
GET  /approvals/check/{type}/{id} Check approval status
POST /approvals/{id}/execute      Mark as executed
```

**Database Tables**:
- `approvals`: Approval records with audit trail

**Service**: `backend/app/services/approvals.py`

### H. Evaluation Harness

**Purpose**: Regression testing for AI outputs.

**Key Features**:
- Golden test cases per state
- Deadline derivation testing
- Required clause testing
- State pack contract testing
- UAT checklist generation

**Service**: `backend/app/services/eval_harness.py`

**Usage**:
```python
from app.services.eval_harness import EvalHarness

harness = EvalHarness()
report = harness.run_all_tests(state="TX")
validation = harness.validate_state_pack("TX")
checklist = generate_uat_checklist("TX")
```

### I. State Similarities & Differences (`/rules/summary/*` endpoints)

**Purpose**: Cross-state comparison and analysis.

**Key Features**:
- Common-core requirements
- State clustering (quick-take, commissioners, etc.)
- State-specific deltas
- Markdown/JSON export

**API Endpoints**:
```
GET  /rules/summary/common        Common-core requirements
GET  /rules/summary/clusters      State clusters
GET  /rules/summary/state/{state} State summary
GET  /rules/summary/state/{state}/deltas  State deltas
GET  /rules/summary/compare       Compare states
GET  /rules/summary/export/markdown  Export as markdown
GET  /rules/summary/export/json   Export as JSON
GET  /rules/summary/matrix        Comparison matrix
```

**Service**: `backend/app/services/state_summary.py`

## Database Schema Additions

### New Tables

```sql
-- Evidence-Grade Citation System
CREATE TABLE sources (
    id VARCHAR PRIMARY KEY,
    title VARCHAR NOT NULL,
    jurisdiction VARCHAR NOT NULL,
    authority_level VARCHAR NOT NULL,
    citation_string VARCHAR,
    content_hash VARCHAR NOT NULL,
    raw_text_path VARCHAR,
    raw_text_snippet TEXT,
    verified BOOLEAN DEFAULT FALSE,
    verified_by VARCHAR REFERENCES users(id),
    verified_at TIMESTAMP,
    retrieved_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE citations (
    id VARCHAR PRIMARY KEY,
    source_id VARCHAR NOT NULL REFERENCES sources(id),
    used_in_type VARCHAR NOT NULL,
    used_in_id VARCHAR NOT NULL,
    snippet TEXT,
    snippet_hash VARCHAR NOT NULL,
    span_start INTEGER,
    span_end INTEGER,
    section VARCHAR,
    verified BOOLEAN DEFAULT FALSE,
    verification_status VARCHAR DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- AI Telemetry
CREATE TABLE ai_events (
    id VARCHAR PRIMARY KEY,
    action VARCHAR NOT NULL,
    model VARCHAR NOT NULL,
    prompt_hash VARCHAR NOT NULL,
    inputs_hash VARCHAR NOT NULL,
    outputs_hash VARCHAR NOT NULL,
    inputs_json JSONB NOT NULL,
    outputs_json JSONB NOT NULL,
    latency_ms INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_estimate_usd NUMERIC,
    project_id VARCHAR REFERENCES projects(id),
    parcel_id VARCHAR REFERENCES parcels(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Approval Workflow
CREATE TABLE approvals (
    id VARCHAR PRIMARY KEY,
    entity_type VARCHAR NOT NULL,
    entity_id VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'draft',
    content_hash VARCHAR NOT NULL,
    requested_by VARCHAR REFERENCES users(id),
    approved_by VARCHAR REFERENCES users(id),
    approved_at TIMESTAMP,
    rejected_by VARCHAR REFERENCES users(id),
    rejection_reason TEXT,
    audit_trail JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Requirements Ops
CREATE TABLE requirement_packs (
    id VARCHAR PRIMARY KEY,
    jurisdiction VARCHAR NOT NULL,
    version VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'draft',
    yaml_content TEXT NOT NULL,
    content_hash VARCHAR NOT NULL,
    published_at TIMESTAMP,
    published_by VARCHAR REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE requirements (
    id VARCHAR PRIMARY KEY,
    requirement_id VARCHAR NOT NULL,
    pack_id VARCHAR NOT NULL REFERENCES requirement_packs(id),
    state VARCHAR NOT NULL,
    topic VARCHAR NOT NULL,
    trigger_event VARCHAR,
    required_action VARCHAR NOT NULL,
    deadline_days INTEGER,
    citations JSONB NOT NULL,
    authority_level VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- QA Reports
CREATE TABLE qa_reports (
    id VARCHAR PRIMARY KEY,
    document_id VARCHAR NOT NULL REFERENCES documents(id),
    document_hash VARCHAR NOT NULL,
    jurisdiction VARCHAR,
    risk_level VARCHAR NOT NULL,
    passed BOOLEAN NOT NULL,
    checks_performed INTEGER NOT NULL,
    requires_counsel_review BOOLEAN DEFAULT FALSE,
    checked_at TIMESTAMP DEFAULT NOW()
);
```

## Usage Examples

### Adding a New State Pack

```python
from app.services.requirements_ops import RequirementsOpsService

service = RequirementsOpsService()

# 1. Import the pack
yaml_content = open("rules/ny.yaml").read()
result = service.import_state_pack("NY", yaml_content)
pack_id = result["pack"]["id"]

# 2. Validate
validation = service.validate_pack(pack_id)
if not validation.valid:
    print(f"Errors: {validation.errors}")
    exit(1)

# 3. Publish
service.publish_pack(pack_id, "user-123")
```

### Pre-Send Document Validation

```python
from app.services.qa_checks import QACheckService, calculate_risk_score
from app.services.approvals import ApprovalService, ApprovalRequest, ApprovalGate

# 1. Run QA checks
qa_service = QACheckService()
report = qa_service.check_document(
    document_content=content,
    document_id="doc-123",
    jurisdiction="TX",
    document_type="offer_letter",
    context={"parties": [{"name": "John Doe", "role": "owner"}]}
)

if not report.passed:
    print(f"QA Failed: {report.critical_issues}")
    exit(1)

# 2. Request approval
approval_service = ApprovalService()
approval = approval_service.request_approval(
    ApprovalRequest(
        entity_type="document",
        entity_id="doc-123",
        action="send",
        content_hash=sha256(content),
    ),
    user_id="agent-001"
)

# 3. Wait for counsel approval...

# 4. Check approval before sending
gate = ApprovalGate(approval_service)
gate.require("document", "doc-123", "send", content_hash)

# 5. Send document
send_document(...)

# 6. Mark executed
approval_service.mark_executed(approval.id, final_hash)
```

### Running Regression Tests

```python
from app.services.eval_harness import EvalHarness

harness = EvalHarness()

# Run all tests
report = harness.run_all_tests()
print(f"Results: {report.passed}/{report.total_tests} passed")

# Validate a state pack before publishing
validation = harness.validate_state_pack("TX")
if not validation["pack_valid"]:
    print("Critical failures:", validation["critical_failures"])
    exit(1)

# Generate UAT checklist
checklist = generate_uat_checklist("TX")
with open("uat_checklist_tx.md", "w") as f:
    f.write(checklist)
```

## Security & Privacy Considerations

### Data Handling Controls
- All documents have privilege tags (privileged/work_product/public)
- PII redaction before non-privileged exports
- Strict RBAC on AI traces and source text

### Prompt Injection Defenses
- Sanitize landowner uploads before LLM input
- Isolate retrieval context from user text
- Input validation on all user-provided content

### High-Sensitivity Routing
- Configurable model routing based on document sensitivity
- Option to restrict external API calls for sensitive docs

## Testing

Run all AI-first module tests:

```bash
cd backend
pytest tests/test_requirements_ops.py
pytest tests/test_citations.py
pytest tests/test_approvals.py
pytest tests/test_eval_harness.py
```

## Future Enhancements

1. **Regulatory Update Monitor**: Implement actual API integrations with Westlaw, LexisNexis, and state legislature feeds
2. **LangChain Integration**: Add tool interfaces for StatuteRetrieverTool, PackLookupTool, DeadlineCalcTool
3. **Multi-Agent Orchestration**: Implement OversightAgent for routing and escalation
4. **Advanced Citation Verification**: Semantic matching for paraphrased citations
5. **Golden Test Expansion**: Add 2-3 test cases per state for all 50 states
