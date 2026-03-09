# Milestone 1: Technical Design & Product Refinement

**Duration:** February 4, 2026 - March 3, 2026  
**Sprints:** 1-2  
**Status:** Complete

This document provides visual diagrams and comprehensive documentation for the LandRight MVP technical design.

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Database Schema (ERD)](#2-database-schema-erd)
3. [API Structure](#3-api-structure)
4. [Deployment Architecture](#4-deployment-architecture)
5. [Key Data Flows](#5-key-data-flows)
6. [Technology Stack](#6-technology-stack)
7. [Security Architecture](#7-security-architecture)

---

## 1. System Architecture

### High-Level Component Diagram

```mermaid
flowchart TB
    subgraph clients [Client Layer]
        WebApp[React Web App<br/>Vite + TypeScript]
        Portal[Landowner Portal<br/>Magic Link Auth]
        Mobile[Mobile Browser]
    end

    subgraph gateway [API Gateway]
        LB[Cloud Load Balancer]
        CDN[Cloud CDN]
    end

    subgraph backend [Backend Services]
        API[FastAPI<br/>Main API Server]
        Worker[Celery Workers<br/>Async Tasks]
        Scheduler[Celery Beat<br/>Scheduled Jobs]
    end

    subgraph ai [AI Services]
        RAG[RAG Engine<br/>Knowledge Base]
        LLM[LLM Integration<br/>OpenAI/Anthropic]
        Copilot[AI Copilot<br/>Legal Assistant]
    end

    subgraph data [Data Layer]
        PG[(PostgreSQL 16<br/>+ PostGIS)]
        Redis[(Redis 7<br/>Cache + Queue)]
        GCS[Cloud Storage<br/>Documents]
    end

    subgraph external [External Services]
        DocuSign[DocuSign<br/>E-Signatures]
        SendGrid[SendGrid<br/>Email]
        Mapbox[Mapbox<br/>GIS/Maps]
        Clerk[Clerk/Auth0<br/>Identity]
    end

    clients --> gateway
    gateway --> backend
    backend --> ai
    backend --> data
    backend --> external
    Worker --> data
    Worker --> external
    ai --> LLM
    ai --> PG
```

### Component Responsibilities

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| Web App | React + Vite | Internal user interface (agents, counsel, ops) |
| Portal | React | Landowner-facing portal with magic link auth |
| API Server | FastAPI | REST API, business logic, RBAC |
| Workers | Celery | Async document generation, batch comms |
| RAG Engine | LangChain | Legal knowledge retrieval |
| PostgreSQL | v16 + PostGIS | Primary data store with spatial support |
| Redis | v7 | Caching, task queue, session store |
| Cloud Storage | GCS | Document and evidence storage |

---

## 2. Database Schema (ERD)

### Core Domain Model

```mermaid
erDiagram
    PROJECT ||--o{ PARCEL : contains
    PROJECT ||--o{ ALIGNMENT : has
    PROJECT ||--o{ BUDGET : tracks
    
    PARCEL ||--o{ PARTY : "linked via ParcelParty"
    PARCEL ||--o{ NOTICE : receives
    PARCEL ||--o{ ROE : has
    PARCEL ||--o{ LITIGATION_CASE : may_have
    PARCEL ||--o{ OFFER : receives
    PARCEL ||--|| PAYMENT_LEDGER : tracks
    PARCEL ||--o{ TITLE_INSTRUMENT : has
    PARCEL ||--o{ CURATIVE_ITEM : requires
    PARCEL ||--o{ COMMUNICATION : receives
    PARCEL ||--o{ SEGMENT : divided_into
    
    ALIGNMENT ||--o{ SEGMENT : contains
    
    NOTICE ||--o{ SERVICE_ATTEMPT : tracked_by
    
    ROE ||--o{ ROE_FIELD_EVENT : logs
    
    OFFER ||--o| OFFER : supersedes
    OFFER }o--|| PAYMENT_LEDGER : updates

    PROJECT {
        uuid id PK
        string name
        string jurisdiction
        enum stage
        geometry boundary
        timestamp created_at
    }
    
    PARCEL {
        uuid id PK
        uuid project_id FK
        string apn
        enum stage
        geometry geometry
        string address
        timestamp created_at
    }
    
    PARTY {
        uuid id PK
        string name
        string email
        string phone
        enum party_type
    }
    
    NOTICE {
        uuid id PK
        uuid parcel_id FK
        enum notice_type
        date sent_date
        date deadline
    }
    
    ROE {
        uuid id PK
        uuid parcel_id FK
        enum status
        date effective_date
        date expiry_date
    }
    
    LITIGATION_CASE {
        uuid id PK
        uuid parcel_id FK
        string case_number
        enum status
        boolean quick_take
    }
    
    OFFER {
        uuid id PK
        uuid parcel_id FK
        enum offer_type
        enum status
        uuid previous_offer_id FK
    }
    
    PAYMENT_LEDGER {
        uuid id PK
        uuid parcel_id FK
        enum payment_status
        uuid current_offer_id FK
    }
```

### Document & Template Model

```mermaid
erDiagram
    TEMPLATE ||--o{ DOCUMENT : generates
    DOCUMENT ||--o{ QA_REPORT : validated_by
    QA_REPORT ||--o{ QA_CHECK : contains
    
    DOCUMENT ||--o| TITLE_INSTRUMENT : is_a
    DOCUMENT ||--o| ESIGN_ENVELOPE : attached_to
    
    SOURCE ||--o{ CITATION : provides
    CITATION ||--o{ QA_CHECK : validates
    
    TEMPLATE {
        uuid id PK
        string name
        string jurisdiction
        int version
        text content
        json schema
    }
    
    DOCUMENT {
        uuid id PK
        uuid template_id FK
        string filename
        string storage_path
        uuid created_by FK
    }
    
    QA_REPORT {
        uuid id PK
        uuid document_id FK
        boolean passed
        float risk_score
    }
    
    QA_CHECK {
        uuid id PK
        uuid report_id FK
        enum check_type
        boolean passed
        text finding
    }
    
    SOURCE {
        uuid id PK
        enum authority_level
        string citation
        text content
    }
    
    CITATION {
        uuid id PK
        uuid source_id FK
        string claim
        float confidence
    }
```

### AI & Workflow Model

```mermaid
erDiagram
    AI_DECISION ||--o{ ESCALATION_REQUEST : may_trigger
    AI_DECISION ||--o{ AI_EVENT : logged_by
    
    WORKFLOW_ESCALATION }o--|| PARCEL : for
    WORKFLOW_ESCALATION }o--o| USER : assigned_to
    
    APPROVAL }o--|| USER : reviewed_by
    
    PORTAL_INVITE ||--o{ PORTAL_SESSION : creates
    PORTAL_INVITE }o--|| PARCEL : for
    
    CHAT_THREAD ||--o{ CHAT_MESSAGE : contains
    
    AI_DECISION {
        uuid id PK
        string decision_type
        json input_data
        json output_data
        uuid reviewed_by FK
    }
    
    AI_EVENT {
        uuid id PK
        uuid decision_id FK
        string event_type
        json telemetry
        float cost_usd
    }
    
    ESCALATION_REQUEST {
        uuid id PK
        uuid decision_id FK
        enum priority
        text reason
    }
    
    WORKFLOW_ESCALATION {
        uuid id PK
        uuid parcel_id FK
        string from_stage
        string to_stage
        uuid assigned_to FK
    }
    
    APPROVAL {
        uuid id PK
        string entity_type
        uuid entity_id
        enum status
        uuid reviewer_id FK
    }
    
    PORTAL_SESSION {
        uuid id PK
        uuid invite_id FK
        timestamp expires_at
        string ip_address
    }
```

### Key Enums Reference

| Enum | Values | Usage |
|------|--------|-------|
| `ProjectStage` | INTAKE, NEGOTIATION, LITIGATION, CLOSED | Project lifecycle |
| `ParcelStage` | INTAKE, APPRAISAL, OFFER_PENDING, OFFER_SENT, NEGOTIATION, CLOSING, LITIGATION, CLOSED | Parcel workflow |
| `Persona` | LANDOWNER, LAND_AGENT, IN_HOUSE_COUNSEL, OUTSIDE_COUNSEL, FIRM_ADMIN, ADMIN | RBAC roles |
| `NoticeType` | INITIAL_OUTREACH, OFFER, STATUTORY, FINAL_OFFER, POSSESSION | Notice categories |
| `ROEStatus` | DRAFT, SENT, SIGNED, ACTIVE, EXPIRED, REVOKED | ROE lifecycle |
| `LitigationStatus` | NOT_FILED, FILED, SERVED, COMMISSIONERS_HEARING, ORDER_OF_POSSESSION, TRIAL, APPEAL, SETTLED, CLOSED | Case progression |
| `OfferStatus` | DRAFT, SENT, RECEIVED, ACCEPTED, REJECTED, EXPIRED, SUPERSEDED | Offer workflow |
| `PaymentStatus` | NOT_STARTED, INITIAL_OFFER_SENT, COUNTEROFFER_RECEIVED, AGREEMENT_IN_PRINCIPLE, PAYMENT_INSTRUCTION_SENT, PAYMENT_CLEARED | Payment tracking |

---

## 3. API Structure

### API Domain Organization

```mermaid
flowchart LR
    subgraph core [Core Operations]
        Cases[/cases/]
        Parcels[/parcels/]
        Workflows[/workflows/]
    end
    
    subgraph legal [Legal Operations]
        Litigation[/litigation/]
        ROE[/roe/]
        Deadlines[/deadlines/]
        Title[/title/]
        Offers[/offers/]
    end
    
    subgraph docs [Documents]
        Templates[/templates/]
        QA[/qa/]
        Binder[/binder/]
    end
    
    subgraph comms [Communications]
        Communications[/communications/]
        Chat[/chat/]
        Portal[/portal/]
        Notifications[/notifications/]
    end
    
    subgraph ai_ops [AI & Analytics]
        AI[/ai/]
        Agents[/agents/]
        Copilot[/copilot/]
        RAG[/rag/]
        Analytics[/analytics/]
    end
    
    subgraph admin_ops [Admin & Ops]
        Admin[/admin/]
        Rules[/rules/]
        Approvals[/approvals/]
        Health[/health/]
    end
    
    subgraph integrations [Integrations]
        ESign[/esign/]
        Alignments[/alignments/]
        Integrations_ext[/integrations/]
    end
```

### Endpoint Count by Domain

| Domain | Route File | Endpoints | Description |
|--------|------------|-----------|-------------|
| **Core** | cases, parcels, workflows | 15 | Case/parcel CRUD, state transitions |
| **Legal** | litigation, roe, deadlines, title, offers | 35 | Legal document management |
| **Documents** | templates, qa, binder | 12 | Document generation & QA |
| **Communications** | communications, chat, portal, notifications | 28 | Multi-channel messaging |
| **AI** | ai, agents, copilot, rag, analytics | 25 | AI-powered features |
| **Admin** | admin, rules, approvals, health | 30 | Administration & compliance |
| **Integrations** | esign, alignments, integrations | 18 | External service connectors |
| **Total** | 35 files | **163+** | Full MVP API |

### Authentication & Authorization

```mermaid
flowchart TD
    Request[Incoming Request] --> AuthCheck{Auth Type?}
    
    AuthCheck -->|Internal User| JWT[JWT Token]
    AuthCheck -->|Portal User| Cookie[Session Cookie]
    AuthCheck -->|Webhook| APIKey[API Key]
    
    JWT --> ValidateJWT[Validate JWT]
    Cookie --> ValidateSession[Validate Portal Session]
    APIKey --> ValidateKey[Validate API Key]
    
    ValidateJWT --> GetPersona[Get Persona from Token]
    ValidateSession --> GetPortalPersona[Set Persona: LANDOWNER]
    ValidateKey --> GetServicePersona[Set Persona: SYSTEM]
    
    GetPersona --> RBAC{RBAC Check}
    GetPortalPersona --> RBAC
    GetServicePersona --> RBAC
    
    RBAC -->|Allowed| Execute[Execute Request]
    RBAC -->|Denied| Forbidden[403 Forbidden]
    
    Execute --> AuditLog[Log Audit Event]
    AuditLog --> Response[Return Response]
```

### RBAC Permission Matrix (Summary)

| Resource | Landowner | Land Agent | In-House Counsel | Outside Counsel | Firm Admin | Admin |
|----------|-----------|------------|------------------|-----------------|------------|-------|
| Parcel | R (own) | RW | RW | R | R | R |
| Offer | R (own) | RW | RW | R | R | R |
| Communication | RW (own) | RW | RW | R | R | R |
| Litigation | - | R | RW | RW | R | R |
| ROE | R (own) | RW | RW | R | R | R |
| Template | - | R | RW | R | - | RW |
| Admin Dashboard | - | - | - | - | R | RW |

---

## 4. Deployment Architecture

### GCP Infrastructure

```mermaid
flowchart TB
    subgraph internet [Internet]
        Users[Users]
        Webhooks[Webhook Sources]
    end
    
    subgraph gcp [Google Cloud Platform]
        subgraph edge [Edge Services]
            GLB[Global Load Balancer]
            CDN[Cloud CDN]
            Armor[Cloud Armor<br/>WAF]
        end
        
        subgraph compute [Compute - Cloud Run]
            API1[API Instance 1]
            API2[API Instance 2]
            APIx[API Instance N]
            Worker1[Worker Instance 1]
            Worker2[Worker Instance 2]
        end
        
        subgraph data_layer [Data Services]
            CloudSQL[(Cloud SQL<br/>PostgreSQL 16)]
            MemStore[(Memorystore<br/>Redis 7)]
            GCS[Cloud Storage<br/>Documents]
        end
        
        subgraph security [Security]
            SM[Secret Manager]
            KMS[Cloud KMS]
            IAM[IAM]
        end
        
        subgraph observability [Observability]
            Logging[Cloud Logging]
            Monitoring[Cloud Monitoring]
            Trace[Cloud Trace]
            Sentry[Sentry<br/>Error Tracking]
        end
    end
    
    Users --> GLB
    Webhooks --> GLB
    GLB --> Armor
    Armor --> CDN
    CDN --> compute
    
    compute --> data_layer
    compute --> security
    compute --> observability
```

### Environment Configuration

| Environment | API URL | Database | Redis | Purpose |
|-------------|---------|----------|-------|---------|
| **Local** | localhost:8050 | localhost:55432 | localhost:56379 | Development |
| **Staging** | api-staging.landright.ai | staging-db | staging-redis | QA/Testing |
| **Production** | api.landright.ai | prod-db (HA) | prod-redis (HA) | Live system |

### Scaling Configuration

```yaml
# Cloud Run Scaling
min_instances: 2
max_instances: 100
cpu: 2
memory: 4Gi

# Autoscaling Triggers
cpu_utilization: 70%
request_count: 100/instance
concurrent_requests: 80

# Database
machine_type: db-custom-4-16384
high_availability: true
backup_retention: 30 days

# Redis
tier: standard
memory_size_gb: 5
replica_count: 1
```

---

## 5. Key Data Flows

### Landowner Portal Flow

```mermaid
sequenceDiagram
    participant LO as Landowner
    participant Portal as Portal UI
    participant API as FastAPI
    participant DB as PostgreSQL
    participant Email as SendGrid
    participant ESign as DocuSign
    
    Note over LO,ESign: Magic Link Authentication
    LO->>Portal: Request Access
    Portal->>API: POST /portal/invites
    API->>DB: Create PortalInvite (hashed token)
    API->>Email: Send magic link email
    Email-->>LO: Email with link
    LO->>Portal: Click magic link
    Portal->>API: POST /portal/verify
    API->>DB: Validate token, create session
    API-->>Portal: Session cookie + parcel data
    
    Note over LO,ESign: Decision Flow
    Portal->>API: GET /portal/decision/options
    API-->>Portal: Accept/Counter/Call options
    LO->>Portal: Select "Accept Offer"
    Portal->>API: POST /portal/decision
    API->>DB: Update offer status
    API->>ESign: POST /esign/initiate
    ESign-->>LO: Signing email
    LO->>ESign: Sign documents
    ESign->>API: POST /esign/webhook (completed)
    API->>DB: Update status to SIGNED
```

### Document Generation & QA Flow

```mermaid
sequenceDiagram
    participant Agent as Land Agent
    participant UI as Web App
    participant API as FastAPI
    participant Worker as Celery Worker
    participant AI as AI Service
    participant QA as QA Engine
    participant DB as PostgreSQL
    
    Agent->>UI: Request offer letter
    UI->>API: POST /templates/render
    API->>DB: Get template + parcel data
    API->>Worker: Queue render task
    Worker->>AI: Generate AI draft sections
    AI-->>Worker: Draft content
    Worker->>DB: Save Document
    Worker-->>API: Document ready
    
    Note over Agent,DB: QA Validation
    API->>QA: POST /qa/check
    QA->>DB: Load required clauses (jurisdiction)
    QA->>AI: Validate citations
    QA-->>API: QA Report (pass/fail)
    API->>DB: Save QAReport + QAChecks
    
    alt QA Passed
        API-->>UI: Document ready for review
        Agent->>UI: Approve document
        UI->>API: POST /approvals/request
    else QA Failed
        API-->>UI: Show issues
        Agent->>UI: Fix issues, resubmit
    end
```

### Litigation Workflow

```mermaid
sequenceDiagram
    participant Counsel as Counsel
    participant UI as Web App
    participant API as FastAPI
    participant DB as PostgreSQL
    participant Calendar as Deadline Engine
    participant Outside as Outside Counsel
    
    Counsel->>UI: Initiate litigation
    UI->>API: POST /litigation
    API->>DB: Create LitigationCase
    API->>Calendar: POST /deadlines/derive
    Calendar->>DB: Load jurisdiction rules
    Calendar->>DB: Create statutory deadlines
    Calendar-->>API: Deadlines created
    
    Note over Counsel,Outside: Case Progression
    loop Status Updates
        Outside->>API: POST /outside/status
        API->>DB: Update case status
        API->>DB: Log StatusChange history
        API->>Calendar: Recalculate deadlines
    end
    
    Counsel->>UI: View case timeline
    UI->>API: GET /litigation/{id}/history
    API-->>UI: Full status history
    
    Counsel->>UI: Export to calendar
    UI->>API: GET /deadlines/ical
    API-->>Counsel: iCal file download
```

### ROE Field Operations Flow

```mermaid
sequenceDiagram
    participant Agent as Field Agent
    participant Mobile as Mobile Browser
    participant API as FastAPI
    participant DB as PostgreSQL
    participant GIS as Mapbox
    
    Agent->>Mobile: Open ROE list
    Mobile->>API: GET /roe?parcel_id=X
    API-->>Mobile: Active ROEs
    
    Agent->>Mobile: Start field visit
    Mobile->>GIS: Get current location
    GIS-->>Mobile: Coordinates
    Mobile->>API: POST /roe/{id}/field-events
    Note right of API: event_type: CHECK_IN<br/>lat/lng, timestamp
    API->>DB: Create ROEFieldEvent
    
    Note over Agent,DB: Field Work
    Agent->>Mobile: Complete inspection
    Mobile->>API: POST /roe/{id}/field-events
    Note right of API: event_type: CHECK_OUT<br/>notes, photos
    API->>DB: Create ROEFieldEvent
    
    Agent->>Mobile: View ROE map
    Mobile->>API: GET /alignments/segments?parcel_id=X
    API-->>Mobile: Segment geometries
    Mobile->>GIS: Render on map
```

---

## 6. Technology Stack

### Backend Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Framework** | FastAPI | 0.109+ | Async REST API |
| **ORM** | SQLAlchemy | 2.0+ | Database abstraction |
| **Validation** | Pydantic | 2.0+ | Request/response models |
| **Task Queue** | Celery | 5.3+ | Async job processing |
| **Cache** | Redis | 7.0+ | Caching, sessions, queue broker |
| **Database** | PostgreSQL | 16 | Primary data store |
| **Spatial** | PostGIS | 3.4+ | GIS operations |

### Frontend Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Framework** | React | 18+ | UI components |
| **Build Tool** | Vite | 5+ | Fast dev server, bundling |
| **Language** | TypeScript | 5+ | Type safety |
| **Styling** | Tailwind CSS | 3+ | Utility-first CSS |
| **Maps** | Mapbox GL | 3+ | Interactive maps |
| **State** | React hooks | - | Local state management |

### AI Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **LLM** | OpenAI GPT-4 / Anthropic Claude | Document generation, analysis |
| **RAG** | LangChain + pgvector | Legal knowledge retrieval |
| **Embeddings** | OpenAI Ada | Document vectorization |

### Infrastructure

| Service | GCP Product | Purpose |
|---------|-------------|---------|
| **Compute** | Cloud Run | Containerized API + workers |
| **Database** | Cloud SQL | Managed PostgreSQL |
| **Cache** | Memorystore | Managed Redis |
| **Storage** | Cloud Storage | Document storage |
| **CDN** | Cloud CDN | Static asset delivery |
| **Security** | Cloud Armor | WAF, DDoS protection |
| **Secrets** | Secret Manager | Credential management |
| **Monitoring** | Cloud Monitoring | Metrics, alerts |
| **Logging** | Cloud Logging | Centralized logs |

---

## 7. Security Architecture

### Security Layers

```mermaid
flowchart TB
    subgraph perimeter [Perimeter Security]
        WAF[Cloud Armor WAF]
        DDoS[DDoS Protection]
        TLS[TLS 1.3 Termination]
    end
    
    subgraph app [Application Security]
        Auth[Authentication<br/>JWT + Magic Link]
        RBAC_sec[RBAC Authorization]
        Validation[Input Validation<br/>Pydantic]
        RateLimit[Rate Limiting]
    end
    
    subgraph data_sec [Data Security]
        Encryption[Encryption at Rest<br/>CMEK]
        TLS_int[Encryption in Transit<br/>TLS]
        RLS[Row-Level Security]
        Masking[Data Masking<br/>PII]
    end
    
    subgraph audit_sec [Audit & Compliance]
        AuditLog[Audit Logging]
        SIEM[Security Monitoring]
        Backup[Encrypted Backups]
    end
    
    perimeter --> app
    app --> data_sec
    data_sec --> audit_sec
```

### Security Controls Summary

| Control | Implementation | Status |
|---------|---------------|--------|
| **Authentication** | JWT (internal), Magic Link (portal) | Implemented |
| **Authorization** | RBAC with persona matrix | Implemented |
| **Encryption (Transit)** | TLS 1.3 everywhere | Implemented |
| **Encryption (Rest)** | CMEK via Cloud KMS | Implemented |
| **Input Validation** | Pydantic models | Implemented |
| **Rate Limiting** | Per-endpoint limits | Implemented |
| **Audit Logging** | All state changes logged | Implemented |
| **Secrets Management** | GCP Secret Manager | Implemented |
| **Vulnerability Scanning** | Dependabot + Snyk | Configured |
| **Penetration Testing** | Scheduled quarterly | Planned |

---

## Appendix: File References

| Document | Path | Description |
|----------|------|-------------|
| Architecture | `docs/architecture.md` | Detailed architecture narrative |
| Data Model | `docs/data-model.md` | Entity descriptions |
| API Reference | `docs/api-reference.md` | Endpoint documentation |
| RBAC | `docs/rbac.md` | Permission matrix |
| Security | `docs/security.md` | Security controls |
| Deployment | `docs/production-deployment.md` | Deployment guide |
| Database Models | `backend/app/db/models.py` | SQLAlchemy models |
| API Routes | `backend/app/api/routes/` | Route implementations |

---

*Generated: February 2026*  
*Version: 1.0*
