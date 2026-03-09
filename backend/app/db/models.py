from datetime import datetime, date
from typing import Optional
from enum import Enum as PyEnum
from sqlalchemy import (
    Column,
    DateTime,
    String,
    Text,
    ForeignKey,
    Boolean,
    Integer,
    Numeric,
    JSON,
    Enum,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class ProjectStage(str, PyEnum):
    INTAKE = "intake"
    NEGOTIATION = "negotiation"
    LITIGATION = "litigation"
    CLOSED = "closed"


class ParcelStage(str, PyEnum):
    """Parcel-level stage progression following the 8-phase eminent domain workflow."""
    INTAKE = "intake"
    APPRAISAL = "appraisal"
    OFFER_PENDING = "offer_pending"
    OFFER_SENT = "offer_sent"
    NEGOTIATION = "negotiation"
    CLOSING = "closing"
    LITIGATION = "litigation"
    CLOSED = "closed"


# Valid stage transitions for parcels
PARCEL_STAGE_TRANSITIONS: dict[ParcelStage, list[ParcelStage]] = {
    ParcelStage.INTAKE: [ParcelStage.APPRAISAL],
    ParcelStage.APPRAISAL: [ParcelStage.OFFER_PENDING],
    ParcelStage.OFFER_PENDING: [ParcelStage.OFFER_SENT],
    ParcelStage.OFFER_SENT: [ParcelStage.NEGOTIATION],
    ParcelStage.NEGOTIATION: [ParcelStage.CLOSING, ParcelStage.LITIGATION],
    ParcelStage.CLOSING: [ParcelStage.CLOSED],
    ParcelStage.LITIGATION: [ParcelStage.CLOSED],
    ParcelStage.CLOSED: [],
}


class Persona(str, PyEnum):
    LANDOWNER = "landowner"
    LAND_AGENT = "land_agent"
    IN_HOUSE_COUNSEL = "in_house_counsel"
    OUTSIDE_COUNSEL = "outside_counsel"
    FIRM_ADMIN = "firm_admin"  # Law firm admin - sees rolled-up cases for their projects
    ADMIN = "admin"  # Platform admin - sees all cases across all firms


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    jurisdiction_code = Column(String, nullable=False)
    stage = Column(Enum(ProjectStage), default=ProjectStage.INTAKE, nullable=False)
    risk_score = Column(Integer, default=0)
    next_deadline_at = Column(DateTime)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parcels = relationship("Parcel", back_populates="project")
    budgets = relationship("Budget", back_populates="project")


class Parcel(Base):
    __tablename__ = "parcels"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    county_fips = Column(String, nullable=False)
    stage = Column(Enum(ParcelStage), default=ParcelStage.INTAKE, nullable=False)
    risk_score = Column(Integer, default=0)
    next_deadline_at = Column(DateTime)
    geom = Column(JSON)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="parcels")
    parties = relationship("ParcelParty", back_populates="parcel")
    communications = relationship("Communication", back_populates="parcel")
    rule_results = relationship("RuleResult", back_populates="parcel")


class Party(Base):
    __tablename__ = "parties"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String)
    phone = Column(String)
    role = Column(String, nullable=False)
    address = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    parcels = relationship("ParcelParty", back_populates="party")


class ParcelParty(Base):
    __tablename__ = "parcel_parties"

    parcel_id = Column(String, ForeignKey("parcels.id"), primary_key=True)
    party_id = Column(String, ForeignKey("parties.id"), primary_key=True)
    relationship_type = Column(String, nullable=False)

    parcel = relationship("Parcel", back_populates="parties")
    party = relationship("Party", back_populates="parcels")


class TitleInstrument(Base):
    __tablename__ = "title_instruments"

    id = Column(String, primary_key=True)
    parcel_id = Column(String, ForeignKey("parcels.id"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id"))
    metadata_json = Column(JSON, default=dict)
    ocr_payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class Appraisal(Base):
    __tablename__ = "appraisals"

    id = Column(String, primary_key=True)
    parcel_id = Column(String, ForeignKey("parcels.id"), nullable=False)
    completed_at = Column(DateTime)
    value = Column(Numeric)
    comps = Column(JSON)
    summary = Column(Text)
    attachment_id = Column(String, ForeignKey("documents.id"))


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    doc_type = Column(String, nullable=False)
    template_id = Column(String)
    version = Column(String, default="1.0.0")
    sha256 = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    privilege = Column(String, default="non_privileged")
    metadata_json = Column(JSON, default=dict)
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


class Template(Base):
    __tablename__ = "templates"

    id = Column(String, primary_key=True)
    version = Column(String, nullable=False)
    locale = Column(String, default="en-US")
    jurisdiction = Column(String)
    variables_schema = Column(JSON, nullable=False)
    redactions = Column(JSON, default=list)
    privilege = Column(String, default="non_privileged")
    classifications = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class Communication(Base):
    __tablename__ = "communications"

    id = Column(String, primary_key=True)
    parcel_id = Column(String, ForeignKey("parcels.id"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    channel = Column(String, nullable=False)
    direction = Column(String, nullable=False)
    content = Column(Text)
    delivery_status = Column(String, default="pending")
    delivery_proof = Column(JSON)
    sla_due_at = Column(DateTime)
    hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    parcel = relationship("Parcel", back_populates="communications")


class RuleResult(Base):
    __tablename__ = "rule_results"

    id = Column(String, primary_key=True)
    parcel_id = Column(String, ForeignKey("parcels.id"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    rule_id = Column(String, nullable=False)
    version = Column(String, nullable=False)
    citation = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    fired_at = Column(DateTime, default=datetime.utcnow)
    triggered_by = Column(String, ForeignKey("users.id"))

    parcel = relationship("Parcel", back_populates="rule_results")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    parcel_id = Column(String, ForeignKey("parcels.id"))
    title = Column(String, nullable=False)
    assigned_to = Column(String, ForeignKey("users.id"))
    persona = Column(Enum(Persona), nullable=False)
    due_at = Column(DateTime)
    status = Column(String, default="open")
    metadata_json = Column(JSON, default=dict)


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    cap_amount = Column(Numeric, nullable=False)
    actual_amount = Column(Numeric, default=0)
    variance = Column(Numeric, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="budgets")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, nullable=False, unique=True)
    persona = Column(Enum(Persona), nullable=False)
    full_name = Column(String)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    resource = Column(String, nullable=False)
    action = Column(String, nullable=False)
    scope = Column(JSON, default=dict)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    actor_persona = Column(Enum(Persona))
    action = Column(String, nullable=False)
    resource = Column(String, nullable=False)
    payload = Column(JSON, default=dict)
    occurred_at = Column(DateTime, default=datetime.utcnow)
    hash = Column(String, nullable=False)


class PortalInvite(Base):
    __tablename__ = "portal_invites"

    id = Column(String, primary_key=True)
    token_sha256 = Column(String, nullable=False, index=True)
    email = Column(String, nullable=False)
    project_id = Column(String, ForeignKey("projects.id"))
    parcel_id = Column(String, ForeignKey("parcels.id"))
    expires_at = Column(DateTime, nullable=False)
    verified_at = Column(DateTime)
    failed_attempts = Column(Integer, default=0)
    last_failed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class PortalSession(Base):
    """
    Portal session for authenticated landowner access.
    
    Created when a magic link is verified. Sessions can be refreshed
    and are tracked for audit purposes.
    """
    __tablename__ = "portal_sessions"

    id = Column(String, primary_key=True)
    invite_id = Column(String, ForeignKey("portal_invites.id"), nullable=False, index=True)
    session_token = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime)
    ip_address = Column(String)
    user_agent = Column(String)

    # Relationship to invite
    invite = relationship("PortalInvite", backref="sessions")


class EsignEnvelope(Base):
    """
    E-signature envelope tracking.
    
    Stores metadata about documents sent for electronic signature,
    supporting DocuSign and other e-sign providers.
    """
    __tablename__ = "esign_envelopes"

    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    parcel_id = Column(String, ForeignKey("parcels.id"), index=True)
    project_id = Column(String, ForeignKey("projects.id"), index=True)
    status = Column(String, nullable=False, default="draft")  # draft, sent, delivered, signed, completed, declined, voided, expired
    provider = Column(String, nullable=False, default="stub")  # stub, docusign, hellosign
    provider_envelope_id = Column(String)  # External provider's envelope ID
    signers_json = Column(JSON, default=list)  # List of signer info with status
    metadata_json = Column(JSON, default=dict)  # Subject, message, return_url, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    created_by = Column(String, ForeignKey("users.id"))

    # Relationships
    document = relationship("Document", backref="esign_envelopes")


class ChatThread(Base):
    """
    Chat thread for portal messaging between landowners and agents.
    
    Threads are associated with a parcel and support threaded conversations.
    """
    __tablename__ = "chat_threads"

    id = Column(String, primary_key=True)
    parcel_id = Column(String, ForeignKey("parcels.id"), index=True)
    project_id = Column(String, ForeignKey("projects.id"), index=True)
    subject = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")  # open, resolved, archived
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    created_by_persona = Column(Enum(Persona))
    participants_json = Column(JSON, default=list)  # List of persona values

    # Relationships
    messages = relationship("ChatMessage", backref="thread", cascade="all, delete-orphan")


class ChatMessage(Base):
    """
    Individual message within a chat thread.
    
    Supports replies, attachments, and read receipts.
    """
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True)
    thread_id = Column(String, ForeignKey("chat_threads.id"), nullable=False, index=True)
    sender_user_id = Column(String, ForeignKey("users.id"))
    sender_persona = Column(Enum(Persona))
    content = Column(Text, nullable=False)
    message_type = Column(String, default="text")  # text, system, attachment
    reply_to_id = Column(String, ForeignKey("chat_messages.id"))
    attachment_id = Column(String, ForeignKey("documents.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime)
    read_by_persona = Column(Enum(Persona))


class Deadline(Base):
    __tablename__ = "deadlines"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    parcel_id = Column(String, ForeignKey("parcels.id"))
    title = Column(String, nullable=False)
    due_at = Column(DateTime, nullable=False)
    timezone = Column(String, default="UTC")
    created_at = Column(DateTime, default=datetime.utcnow)


class StatusChange(Base):
    __tablename__ = "status_changes"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    parcel_id = Column(String, ForeignKey("parcels.id"))
    old_status = Column(String)
    new_status = Column(String, nullable=False)
    reason = Column(Text)
    actor_persona = Column(Enum(Persona))
    occurred_at = Column(DateTime, default=datetime.utcnow)
    hash = Column(String, nullable=False)


# =============================================================================
# AI Agent Models
# =============================================================================


class AIDecision(Base):
    """Log of all AI agent decisions for audit trail.
    
    Every decision made by an AI agent is recorded here with:
    - Full context hash for reproducibility
    - Confidence score and flags
    - Review status and outcome
    - Tamper-evident hash
    """
    __tablename__ = "ai_decisions"
    
    id = Column(String, primary_key=True)
    agent_type = Column(String, nullable=False)  # IntakeAgent, ComplianceAgent, etc.
    project_id = Column(String, ForeignKey("projects.id"))
    parcel_id = Column(String, ForeignKey("parcels.id"))
    context_hash = Column(String, nullable=False)  # SHA-256 of input context
    result_data = Column(JSON, nullable=False)  # Agent result payload
    confidence = Column(Numeric, nullable=False)  # 0.0-1.0
    flags = Column(JSON, default=list)  # Escalation triggers
    explanation = Column(Text)  # Human-readable explanation
    reviewed_by = Column(String, ForeignKey("users.id"))
    reviewed_at = Column(DateTime)
    review_outcome = Column(String)  # approved, rejected, modified
    occurred_at = Column(DateTime, default=datetime.utcnow)
    hash = Column(String, nullable=False)  # Tamper-evident hash


class EscalationRequest(Base):
    """Escalation requests for human review of AI decisions.
    
    Created when:
    - Agent confidence is below threshold
    - Critical flags are detected
    - Cross-verification disagreement
    - System errors occur
    """
    __tablename__ = "escalation_requests"
    
    id = Column(String, primary_key=True)
    ai_decision_id = Column(String, ForeignKey("ai_decisions.id"), nullable=False)
    reason = Column(String, nullable=False)  # EscalationReason enum value
    priority = Column(String, default="medium")  # low, medium, high, critical
    assigned_to = Column(String, ForeignKey("users.id"))
    status = Column(String, default="open")  # open, in_review, resolved
    resolution = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    
    ai_decision = relationship("AIDecision", backref="escalations")


class EscalationPriority(str, PyEnum):
    """Priority levels for workflow escalations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkflowEscalation(Base):
    """Escalation for workflow stage progressions requiring review.
    
    Created when:
    - Auto-progression confidence is below threshold
    - Manual override is requested
    - Guard conditions partially met
    """
    __tablename__ = "workflow_escalations"
    
    id = Column(String, primary_key=True)
    parcel_id = Column(String, ForeignKey("parcels.id"), nullable=False)
    reason = Column(String, nullable=False)
    priority = Column(Enum(EscalationPriority), default=EscalationPriority.MEDIUM)
    status = Column(String, default="pending")  # pending, approved, rejected
    context_summary = Column(Text)
    target_stage = Column(String)  # The stage we're trying to progress to
    assigned_to = Column(String, ForeignKey("users.id"))
    resolved_by = Column(String, ForeignKey("users.id"))
    resolution_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    
    parcel = relationship("Parcel", backref="workflow_escalations")


class LawChange(Base):
    """Tracked changes in jurisdiction laws/statutes.
    
    Used by ComplianceAgent to:
    - Track detected law changes
    - Generate rule update suggestions
    - Maintain audit trail of legal updates
    """
    __tablename__ = "law_changes"
    
    id = Column(String, primary_key=True)
    jurisdiction = Column(String, nullable=False)  # State code
    source = Column(String, nullable=False)  # Westlaw, legislature, etc.
    change_type = Column(String, nullable=False)  # statute, case_law, regulation
    citation = Column(String)  # Legal citation
    summary = Column(Text, nullable=False)
    full_text = Column(Text)
    effective_date = Column(DateTime)
    detected_at = Column(DateTime, default=datetime.utcnow)
    affects_workflow = Column(Boolean, default=False)
    affected_rules = Column(JSON, default=list)  # Rule IDs affected
    suggested_updates = Column(JSON, default=list)  # Suggested rule changes
    reviewed_by = Column(String, ForeignKey("users.id"))
    reviewed_at = Column(DateTime)
    applied = Column(Boolean, default=False)  # Whether changes were applied


class ExternalDataCache(Base):
    """Cache for external API data (property, AVM, title).
    
    Reduces external API calls and provides fallback
    when external services are unavailable.
    """
    __tablename__ = "external_data_cache"
    
    id = Column(String, primary_key=True)
    cache_type = Column(String, nullable=False)  # property, avm, title, gis, tax
    parcel_id = Column(String, ForeignKey("parcels.id"))
    external_id = Column(String)  # APN, address hash, etc.
    source = Column(String, nullable=False)  # API source name
    data = Column(JSON, nullable=False)
    confidence = Column(Numeric)  # Data confidence/quality score
    fetched_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # TTL for cache entry
    hash = Column(String, nullable=False)  # Data integrity hash


# =============================================================================
# Evidence-Grade Citation & Provenance System (Module B)
# =============================================================================


class AuthorityLevel(str, PyEnum):
    """Authority level of a legal source."""
    CONSTITUTION = "constitution"
    STATUTE = "statute"
    CASE_LAW = "case_law"
    REGULATION = "regulation"
    LOCAL_RULE = "local_rule"
    ADMINISTRATIVE = "administrative"
    SECONDARY = "secondary"


class Source(Base):
    """Evidence source for citations and provenance tracking.
    
    Stores statute text, case excerpts, and other authoritative sources
    with content hashing for integrity verification.
    """
    __tablename__ = "sources"
    
    id = Column(String, primary_key=True)
    url = Column(String)  # Original URL if web-sourced
    title = Column(String, nullable=False)  # Document/case/statute title
    jurisdiction = Column(String, nullable=False)  # State code or "federal"
    authority_level = Column(Enum(AuthorityLevel), nullable=False)
    citation_string = Column(String)  # Formatted legal citation
    effective_date = Column(DateTime)  # When the law became effective
    retrieved_at = Column(DateTime, default=datetime.utcnow)
    content_hash = Column(String, nullable=False)  # SHA-256 of raw_text
    raw_text_path = Column(String)  # Path to full text in storage
    raw_text_snippet = Column(Text)  # First 10KB for quick access
    metadata_json = Column(JSON, default=dict)  # Publisher, version, etc.
    verified = Column(Boolean, default=False)  # Human-verified accuracy
    verified_by = Column(String, ForeignKey("users.id"))
    verified_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    citations = relationship("Citation", back_populates="source")


class Citation(Base):
    """Links AI claims/outputs to authoritative sources.
    
    Every legal assertion in AI output must have a citation
    pointing to a specific span within a Source.
    """
    __tablename__ = "citations"
    
    id = Column(String, primary_key=True)
    source_id = Column(String, ForeignKey("sources.id"), nullable=False)
    
    # Where this citation is used
    used_in_type = Column(String, nullable=False)  # ai_decision, document, rule_result
    used_in_id = Column(String, nullable=False)  # ID of the referencing entity
    
    # Specific text span within source
    span_start = Column(Integer)  # Character offset start
    span_end = Column(Integer)  # Character offset end
    snippet = Column(Text)  # Extracted text snippet
    snippet_hash = Column(String, nullable=False)  # SHA-256 of snippet
    
    # Citation metadata
    page_number = Column(String)  # For PDFs
    section = Column(String)  # e.g., "§21.0113(a)"
    pin_cite = Column(String)  # Precise reference
    
    # Verification
    verified = Column(Boolean, default=False)
    verification_status = Column(String, default="pending")  # pending, verified, disputed
    verification_notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    source = relationship("Source", back_populates="citations")


# =============================================================================
# AI Telemetry & Decision Trace (Module C)
# =============================================================================


class AIEvent(Base):
    """Comprehensive AI telemetry for audit and reproducibility.
    
    Records every AI action with full context for:
    - Audit trail and compliance
    - Debugging and improvement
    - Reproducing exact runs
    - Cost tracking
    """
    __tablename__ = "ai_events"
    
    id = Column(String, primary_key=True)
    
    # Actor and action
    actor_persona = Column(Enum(Persona))  # Who triggered this
    actor_user_id = Column(String, ForeignKey("users.id"))
    action = Column(String, nullable=False)  # generate_draft, evaluate_compliance, etc.
    
    # Prompt and model info
    prompt_template_id = Column(String)  # Template used
    prompt_version = Column(String)  # Version of template
    prompt_hash = Column(String, nullable=False)  # SHA-256 of actual prompt
    model = Column(String, nullable=False)  # gemini-1.5-pro, etc.
    model_version = Column(String)  # Specific version if known
    temperature = Column(Numeric)
    
    # Input/output hashes for reproducibility
    inputs_hash = Column(String, nullable=False)  # SHA-256 of all inputs
    outputs_hash = Column(String, nullable=False)  # SHA-256 of outputs
    
    # Full content (stored in JSON for flexibility)
    inputs_json = Column(JSON, nullable=False)  # Full input payload
    outputs_json = Column(JSON, nullable=False)  # Full output payload
    
    # Tool calls made during execution
    tool_calls = Column(JSON, default=list)  # List of tool invocations
    
    # Retrieval context
    retrieval_set_ids = Column(JSON, default=list)  # Source IDs used for RAG
    retrieval_query = Column(Text)  # Query used for retrieval
    
    # Performance metrics
    latency_ms = Column(Integer)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    total_tokens = Column(Integer)
    cost_estimate_usd = Column(Numeric)  # Estimated cost
    
    # Outcome
    confidence = Column(Numeric)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # Citations from this event
    citation_ids = Column(JSON, default=list)  # List of Citation IDs
    
    # Links to related entities
    project_id = Column(String, ForeignKey("projects.id"))
    parcel_id = Column(String, ForeignKey("parcels.id"))
    ai_decision_id = Column(String, ForeignKey("ai_decisions.id"))
    
    created_at = Column(DateTime, default=datetime.utcnow)


class PromptTemplate(Base):
    """Versioned prompt templates for reproducibility.
    
    Stores all prompts used by the system with versioning
    to enable exact replay of AI runs.
    """
    __tablename__ = "prompt_templates"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)  # Descriptive name
    version = Column(String, nullable=False)  # Semantic version
    category = Column(String, nullable=False)  # compliance, drafting, analysis, etc.
    
    # Template content
    system_prompt = Column(Text)  # System/context prompt
    user_prompt_template = Column(Text, nullable=False)  # User prompt with {variables}
    output_schema = Column(JSON)  # Expected output JSON schema
    
    # Configuration
    default_model = Column(String, default="gemini-1.5-pro")
    default_temperature = Column(Numeric, default=0.2)
    max_tokens = Column(Integer)
    
    # Metadata
    description = Column(Text)
    author = Column(String)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# =============================================================================
# Human-in-Loop Approval Workflow (Module E)
# =============================================================================


class ApprovalStatus(str, PyEnum):
    """Status progression for approval workflow."""
    DRAFT = "draft"
    QA_PASSED = "qa_passed"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"
    FILED = "filed"


class Approval(Base):
    """Tracks human approval for critical legal actions.
    
    Required before any irreversible action like:
    - Sending final offers
    - Filing court documents
    - Recording deeds
    - Settlement agreements
    """
    __tablename__ = "approvals"
    
    id = Column(String, primary_key=True)
    
    # What needs approval
    entity_type = Column(String, nullable=False)  # document, offer, filing, settlement
    entity_id = Column(String, nullable=False)  # ID of the entity
    action = Column(String, nullable=False)  # send, file, record, execute
    
    # Status tracking
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.DRAFT, nullable=False)
    
    # Context
    project_id = Column(String, ForeignKey("projects.id"))
    parcel_id = Column(String, ForeignKey("parcels.id"))
    jurisdiction = Column(String)
    
    # Content verification
    content_hash = Column(String, nullable=False)  # SHA-256 of content at approval time
    diff_from_previous = Column(JSON)  # Changes from last version
    
    # Review workflow
    requested_by = Column(String, ForeignKey("users.id"), nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow)
    
    reviewer_user_id = Column(String, ForeignKey("users.id"))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)
    
    # Approval details
    approved_by = Column(String, ForeignKey("users.id"))
    approved_at = Column(DateTime)
    approval_notes = Column(Text)
    
    # Rejection details
    rejected_by = Column(String, ForeignKey("users.id"))
    rejected_at = Column(DateTime)
    rejection_reason = Column(Text)
    
    # Execution tracking
    executed_at = Column(DateTime)  # When the action was actually performed
    execution_result = Column(JSON)  # Result of the action
    
    # Audit
    final_content_hash = Column(String)  # Hash of final executed content
    audit_trail = Column(JSON, default=list)  # List of all status changes
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# =============================================================================
# Requirements Ops - 50-State Requirement Management (Module A)
# =============================================================================


class RequirementPackStatus(str, PyEnum):
    """Status of a requirement pack."""
    DRAFT = "draft"
    VALIDATING = "validating"
    VALIDATED = "validated"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class RequirementPack(Base):
    """Versioned collection of requirements for a jurisdiction.
    
    Supports:
    - Version history and diffing
    - Validation before activation
    - Rollback capability
    - Multi-state inheritance
    """
    __tablename__ = "requirement_packs"
    
    id = Column(String, primary_key=True)
    
    # Identification
    jurisdiction = Column(String, nullable=False)  # State code
    version = Column(String, nullable=False)  # Semantic version
    name = Column(String)  # Optional friendly name
    
    # Status
    status = Column(Enum(RequirementPackStatus), default=RequirementPackStatus.DRAFT)
    
    # Content
    yaml_content = Column(Text, nullable=False)  # Full YAML content
    content_hash = Column(String, nullable=False)  # SHA-256 of content
    
    # Inheritance
    extends_pack_id = Column(String, ForeignKey("requirement_packs.id"))
    
    # Metadata
    effective_date = Column(DateTime)  # When these rules become effective
    expiration_date = Column(DateTime)  # When these rules expire (if known)
    
    # Citations for the pack
    primary_citation = Column(String)  # Main statute reference
    citations_json = Column(JSON, default=list)  # All relevant citations
    
    # Validation results
    validation_errors = Column(JSON, default=list)
    validation_warnings = Column(JSON, default=list)
    validated_at = Column(DateTime)
    validated_by = Column(String, ForeignKey("users.id"))
    
    # Publishing
    published_at = Column(DateTime)
    published_by = Column(String, ForeignKey("users.id"))
    
    # Change tracking
    change_summary = Column(Text)  # Human description of changes
    change_diff = Column(JSON)  # Structured diff from previous version
    previous_version_id = Column(String, ForeignKey("requirement_packs.id"))
    
    # Audit
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    requirements = relationship("Requirement", back_populates="pack")


class RequirementTopic(str, PyEnum):
    """Topic categories for requirements."""
    NOTICE = "notice"
    OFFER = "offer"
    APPRAISAL = "appraisal"
    COMPENSATION = "compensation"
    TIMELINE = "timeline"
    FILING = "filing"
    HEARING = "hearing"
    TRIAL = "trial"
    APPEAL = "appeal"
    RELOCATION = "relocation"
    PUBLIC_USE = "public_use"
    BLIGHT = "blight"
    ATTORNEY_FEES = "attorney_fees"


class Requirement(Base):
    """Individual requirement in canonical schema.
    
    Normalized structure for all state requirements to enable:
    - Cross-state comparison
    - Automated deadline derivation
    - Compliance checking
    - Common-core analysis
    """
    __tablename__ = "requirements"
    
    id = Column(String, primary_key=True)
    requirement_id = Column(String, nullable=False)  # Canonical ID (e.g., "notice.initial_offer")
    
    pack_id = Column(String, ForeignKey("requirement_packs.id"), nullable=False)
    
    # Classification
    state = Column(String, nullable=False)  # State code
    topic = Column(Enum(RequirementTopic), nullable=False)
    
    # Trigger
    trigger_event = Column(String)  # Event that triggers this requirement
    trigger_conditions = Column(JSON)  # Additional conditions as JSON
    
    # Action
    required_action = Column(String, nullable=False)  # What must be done
    action_description = Column(Text)  # Detailed description
    
    # Timing
    deadline_rule = Column(String)  # e.g., "30_days_after_offer"
    deadline_days = Column(Integer)  # Numeric days if applicable
    deadline_direction = Column(String)  # "before" or "after"
    deadline_business_days = Column(Boolean, default=False)
    
    # Documentation
    doc_requirements = Column(JSON, default=list)  # Required documents
    
    # Legal authority
    citations = Column(JSON, nullable=False)  # List of citation objects
    authority_level = Column(Enum(AuthorityLevel), nullable=False)
    
    # Metadata
    effective_date = Column(DateTime)
    version = Column(String, nullable=False)
    confidence = Column(Numeric, default=1.0)  # Confidence in accuracy
    notes = Column(Text)
    
    # Common-core marker
    is_common_core = Column(Boolean, default=False)  # True if applies to all states
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    pack = relationship("RequirementPack", back_populates="requirements")


# =============================================================================
# Document QA & Risk Scoring (Module D)
# =============================================================================


class QACheckType(str, PyEnum):
    """Types of QA checks."""
    REQUIRED_CLAUSE = "required_clause"
    FORBIDDEN_LANGUAGE = "forbidden_language"
    NAME_CONSISTENCY = "name_consistency"
    DATE_CONSISTENCY = "date_consistency"
    LEGAL_DESCRIPTION = "legal_description"
    DEADLINE_ACCURACY = "deadline_accuracy"
    CITATION_VALIDITY = "citation_validity"
    AMOUNT_ACCURACY = "amount_accuracy"
    SIGNATURE_BLOCK = "signature_block"


class RiskLevel(str, PyEnum):
    """Risk level for QA results."""
    GREEN = "green"  # All checks pass
    YELLOW = "yellow"  # Minor issues, can proceed with caution
    RED = "red"  # Critical issues, must fix before proceeding


class QAReport(Base):
    """QA check results for a document.
    
    Captures all quality checks performed before
    a document can be sent, filed, or exported.
    """
    __tablename__ = "qa_reports"
    
    id = Column(String, primary_key=True)
    
    # What was checked
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    document_version = Column(String)
    document_hash = Column(String, nullable=False)  # Hash of document at check time
    
    # Context
    project_id = Column(String, ForeignKey("projects.id"))
    parcel_id = Column(String, ForeignKey("parcels.id"))
    jurisdiction = Column(String)
    
    # Overall result
    risk_level = Column(Enum(RiskLevel), nullable=False)
    passed = Column(Boolean, nullable=False)
    
    # Detailed checks
    checks_performed = Column(JSON, nullable=False)  # List of check results
    checks_passed = Column(Integer, nullable=False)
    checks_failed = Column(Integer, nullable=False)
    checks_warned = Column(Integer, nullable=False)
    
    # Issues found
    critical_issues = Column(JSON, default=list)  # Red-level issues
    warnings = Column(JSON, default=list)  # Yellow-level issues
    suggestions = Column(JSON, default=list)  # Improvement suggestions
    
    # Required clauses check
    required_clauses_present = Column(JSON, default=list)
    required_clauses_missing = Column(JSON, default=list)
    
    # Citation validation
    citations_validated = Column(Integer, default=0)
    citations_invalid = Column(Integer, default=0)
    citation_issues = Column(JSON, default=list)
    
    # Escalation
    requires_counsel_review = Column(Boolean, default=False)
    escalation_reason = Column(Text)
    
    # Timing
    checked_at = Column(DateTime, default=datetime.utcnow)
    checked_by = Column(String)  # "system" or user_id
    
    # Review
    reviewed_by = Column(String, ForeignKey("users.id"))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)
    override_approved = Column(Boolean, default=False)  # Proceed despite issues
    
    created_at = Column(DateTime, default=datetime.utcnow)


class QACheck(Base):
    """Individual QA check result.
    
    Detailed record of each check performed
    as part of a QA report.
    """
    __tablename__ = "qa_checks"
    
    id = Column(String, primary_key=True)
    report_id = Column(String, ForeignKey("qa_reports.id"), nullable=False)
    
    # Check details
    check_type = Column(Enum(QACheckType), nullable=False)
    check_name = Column(String, nullable=False)  # Human-readable name
    check_description = Column(Text)
    
    # Result
    passed = Column(Boolean, nullable=False)
    risk_level = Column(Enum(RiskLevel), nullable=False)
    
    # Details
    expected_value = Column(Text)  # What was expected
    actual_value = Column(Text)  # What was found
    location = Column(String)  # Where in document (e.g., "page 2, paragraph 3")
    
    # Citation support
    citation_id = Column(String, ForeignKey("citations.id"))
    
    # Error details
    error_message = Column(Text)
    fix_suggestion = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# =============================================================================
# Regulatory Update Monitor (Part of Module A)
# =============================================================================


class RegulatoryUpdate(Base):
    """Proposed regulatory/statutory update.
    
    Created by the Regulatory Update Monitor job
    when changes in law are detected.
    """
    __tablename__ = "regulatory_updates"
    
    id = Column(String, primary_key=True)
    
    # Source of update
    jurisdiction = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # legislature, court, agency
    source_name = Column(String)  # Specific source
    source_url = Column(String)
    
    # Change details
    change_type = Column(String, nullable=False)  # new_statute, amendment, repeal, court_ruling
    effective_date = Column(DateTime)
    
    # Content
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    full_text = Column(Text)
    citation = Column(String)
    
    # Analysis
    impact_assessment = Column(Text)  # AI-generated impact analysis
    affected_requirements = Column(JSON, default=list)  # Requirement IDs affected
    suggested_pack_changes = Column(JSON)  # Proposed YAML changes
    
    # Processing status
    status = Column(String, default="pending")  # pending, reviewed, applied, dismissed
    
    # Review
    detected_at = Column(DateTime, default=datetime.utcnow)
    reviewed_by = Column(String, ForeignKey("users.id"))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)
    
    # Action taken
    applied_to_pack_id = Column(String, ForeignKey("requirement_packs.id"))
    applied_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# =============================================================================
# MVP Core Entities - Agreement Section 3.2 Requirements
# =============================================================================


class NoticeType(str, PyEnum):
    """Types of notices per Agreement Section 3.2(b)."""
    INITIAL_OUTREACH = "initial_outreach"
    OFFER = "offer"
    STATUTORY = "statutory"
    FINAL_OFFER = "final_offer"
    POSSESSION = "possession"


class ServiceMethod(str, PyEnum):
    """Service methods per Agreement Section 3.2(b)."""
    MAIL = "mail"
    CERTIFIED_MAIL = "certified_mail"
    PERSONAL_SERVICE = "personal_service"
    POSTING = "posting"
    PUBLICATION = "publication"


class ServiceOutcome(str, PyEnum):
    """Outcomes for service attempts."""
    PENDING = "pending"
    DELIVERED = "delivered"
    REFUSED = "refused"
    UNDELIVERABLE = "undeliverable"
    NO_ANSWER = "no_answer"


class Notice(Base):
    """Statutory notices per parcel.
    
    Agreement Reference: Section 3.2(b) - Legal-first notices & service engine
    
    Tracks issuance of notices including:
    - Initial outreach letters
    - Offer letters (IOL/FOL)
    - Statutory notices required by jurisdiction
    """
    __tablename__ = "notices"
    
    id = Column(String, primary_key=True)
    parcel_id = Column(String, ForeignKey("parcels.id"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    
    # Notice details
    notice_type = Column(Enum(NoticeType), nullable=False)
    date_issued = Column(DateTime, nullable=False)
    method = Column(Enum(ServiceMethod), nullable=False)
    
    # Linked document
    document_id = Column(String, ForeignKey("documents.id"))
    template_id = Column(String, ForeignKey("templates.id"))
    
    # Jurisdiction-specific
    jurisdiction = Column(String, nullable=False)  # State code
    statutory_citation = Column(String)  # e.g., "Tex. Prop. Code § 21.0113"
    
    # Status tracking
    status = Column(String, default="pending")  # pending, served, failed
    service_complete = Column(Boolean, default=False)
    
    # Metadata
    metadata_json = Column(JSON, default=dict)
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    service_attempts = relationship("ServiceAttempt", back_populates="notice")


class ServiceAttempt(Base):
    """Service attempts for notices.
    
    Agreement Reference: Section 3.2(b) - service attempts tracking
    
    Records each attempt to serve a notice including:
    - Method (mail, personal service, posting)
    - Date and outcome
    - Proof documentation
    """
    __tablename__ = "service_attempts"
    
    id = Column(String, primary_key=True)
    notice_id = Column(String, ForeignKey("notices.id"), nullable=False)
    
    # Attempt details
    attempt_number = Column(Integer, nullable=False, default=1)
    method = Column(Enum(ServiceMethod), nullable=False)
    attempt_date = Column(DateTime, nullable=False)
    outcome = Column(Enum(ServiceOutcome), default=ServiceOutcome.PENDING)
    
    # Proof of service
    proof_document_id = Column(String, ForeignKey("documents.id"))
    proof_description = Column(Text)
    
    # Server info (for personal service)
    server_name = Column(String)
    server_affidavit_id = Column(String, ForeignKey("documents.id"))
    
    # Address used
    address_used = Column(JSON)  # Full address object
    
    # Outcome details
    outcome_notes = Column(Text)
    outcome_date = Column(DateTime)
    
    # Audit
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    notice = relationship("Notice", back_populates="service_attempts")


class ROEStatus(str, PyEnum):
    """Status of Right-of-Entry agreements."""
    DRAFT = "draft"
    SENT = "sent"
    SIGNED = "signed"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class ROE(Base):
    """Right-of-Entry agreements.
    
    Agreement Reference: Section 3.2(c) - ROE management
    
    Tracks ROE agreements including:
    - Templates, effective/expiry dates
    - Access windows and conditions
    - Field check-in/out events
    """
    __tablename__ = "roes"
    
    id = Column(String, primary_key=True)
    parcel_id = Column(String, ForeignKey("parcels.id"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    
    # Agreement details
    template_id = Column(String, ForeignKey("templates.id"))
    document_id = Column(String, ForeignKey("documents.id"))  # Signed ROE
    
    # Dates
    effective_date = Column(DateTime, nullable=False)
    expiry_date = Column(DateTime, nullable=False)
    
    # Status
    status = Column(Enum(ROEStatus), default=ROEStatus.DRAFT)
    
    # Conditions and permitted activities
    conditions = Column(Text)  # Free-form conditions
    permitted_activities = Column(JSON, default=list)  # List of allowed activities
    access_windows = Column(JSON)  # Time windows when access is permitted
    
    # Parties
    landowner_party_id = Column(String, ForeignKey("parties.id"))
    signed_by = Column(String)  # Name of signer
    signed_at = Column(DateTime)
    
    # Notifications
    expiry_warning_sent = Column(Boolean, default=False)
    expiry_warning_date = Column(DateTime)
    
    # Metadata
    metadata_json = Column(JSON, default=dict)
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    field_events = relationship("ROEFieldEvent", back_populates="roe")


class ROEFieldEvent(Base):
    """Field check-in/check-out events for ROE use.
    
    Agreement Reference: Section 3.2(c) - field check-in/out
    """
    __tablename__ = "roe_field_events"
    
    id = Column(String, primary_key=True)
    roe_id = Column(String, ForeignKey("roes.id"), nullable=False)
    
    # Event details
    event_type = Column(String, nullable=False)  # check_in, check_out
    event_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Location
    latitude = Column(Numeric)
    longitude = Column(Numeric)
    
    # Personnel
    user_id = Column(String, ForeignKey("users.id"))
    personnel_name = Column(String)
    
    # Notes and photos
    notes = Column(Text)
    photo_document_ids = Column(JSON, default=list)  # List of document IDs
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    roe = relationship("ROE", back_populates="field_events")


class LitigationStatus(str, PyEnum):
    """Litigation status per Agreement Section 3.2(d)."""
    NOT_FILED = "not_filed"
    FILED = "filed"
    SERVED = "served"
    COMMISSIONERS_HEARING = "commissioners_hearing"
    ORDER_OF_POSSESSION = "order_of_possession"
    TRIAL = "trial"
    APPEAL = "appeal"
    SETTLED = "settled"
    CLOSED = "closed"


class LitigationCase(Base):
    """Litigation cases linked to parcels.
    
    Agreement Reference: Section 3.2(d) - Litigation calendar
    
    Tracks litigation status including:
    - Quick-take vs standard flag
    - Court, cause number, lead counsel
    - Key litigation stage
    """
    __tablename__ = "litigation_cases"
    
    id = Column(String, primary_key=True)
    parcel_id = Column(String, ForeignKey("parcels.id"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    
    # Case identifiers
    cause_number = Column(String)
    court = Column(String, nullable=False)  # Court name
    court_county = Column(String)
    
    # Case type (per Agreement)
    is_quick_take = Column(Boolean, default=False)  # quick-take vs standard flag
    
    # Status
    status = Column(Enum(LitigationStatus), default=LitigationStatus.NOT_FILED)
    
    # Filing info
    filed_date = Column(DateTime)
    filing_document_id = Column(String, ForeignKey("documents.id"))
    
    # Counsel
    lead_counsel_internal = Column(String)  # In-house counsel name
    lead_counsel_internal_id = Column(String, ForeignKey("users.id"))
    lead_counsel_outside = Column(String)  # Outside counsel name
    lead_counsel_outside_firm = Column(String)
    
    # Key dates
    commissioners_hearing_date = Column(DateTime)
    possession_order_date = Column(DateTime)
    trial_date = Column(DateTime)
    
    # Outcome
    settlement_amount = Column(Numeric)
    final_judgment_amount = Column(Numeric)
    closed_date = Column(DateTime)
    
    # Metadata
    metadata_json = Column(JSON, default=dict)
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CurativeStatus(str, PyEnum):
    """Status of curative items."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WAIVED = "waived"


class CurativeItem(Base):
    """Title curative items.
    
    Agreement Reference: Section 3.2(e) - Title & curative tracking
    
    Tracks curative items including:
    - Description (missing heir, unreleased lien, variance issue)
    - Responsible party, due date, status
    """
    __tablename__ = "curative_items"
    
    id = Column(String, primary_key=True)
    parcel_id = Column(String, ForeignKey("parcels.id"), nullable=False)
    title_instrument_id = Column(String, ForeignKey("title_instruments.id"))
    
    # Item details
    item_type = Column(String, nullable=False)  # missing_heir, unreleased_lien, variance, etc.
    description = Column(Text, nullable=False)
    severity = Column(String, default="medium")  # low, medium, high, critical
    
    # Assignment
    responsible_party = Column(String)
    responsible_user_id = Column(String, ForeignKey("users.id"))
    
    # Dates
    identified_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime)
    resolved_date = Column(DateTime)
    
    # Status
    status = Column(Enum(CurativeStatus), default=CurativeStatus.OPEN)
    
    # Resolution
    resolution_notes = Column(Text)
    resolution_document_id = Column(String, ForeignKey("documents.id"))
    
    # Metadata
    metadata_json = Column(JSON, default=dict)
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OfferType(str, PyEnum):
    """Types of offers in negotiation."""
    INITIAL = "initial"
    COUNTEROFFER = "counteroffer"
    FINAL = "final"
    SETTLEMENT = "settlement"


class OfferStatus(str, PyEnum):
    """Status of offers per Agreement Section 3.2(f)."""
    DRAFT = "draft"
    SENT = "sent"
    RECEIVED = "received"  # For counteroffers from landowner
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


class Offer(Base):
    """Negotiation offers and counteroffers.
    
    Agreement Reference: Section 3.2(f) - Payment ledger (status-only)
    
    Tracks offers including:
    - Initial offer, counteroffers, final offer
    - Amount, terms, status
    - No valuation computation (per Agreement exclusions)
    """
    __tablename__ = "offers"
    
    id = Column(String, primary_key=True)
    parcel_id = Column(String, ForeignKey("parcels.id"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    
    # Offer sequence
    offer_type = Column(Enum(OfferType), nullable=False)
    offer_number = Column(Integer, default=1)  # Sequence number
    previous_offer_id = Column(String, ForeignKey("offers.id"))  # Links to prior offer
    
    # Amounts (stored as data, NOT computed - per Agreement 3.3(a))
    amount = Column(Numeric)  # Offer amount
    
    # Terms
    terms = Column(JSON, default=dict)  # Non-monetary terms
    terms_summary = Column(Text)  # Plain-language summary
    
    # Status
    status = Column(Enum(OfferStatus), default=OfferStatus.DRAFT)
    
    # Dates
    created_date = Column(DateTime, default=datetime.utcnow)
    sent_date = Column(DateTime)
    response_due_date = Column(DateTime)
    response_date = Column(DateTime)
    
    # Source
    source = Column(String, default="internal")  # internal, landowner
    landowner_party_id = Column(String, ForeignKey("parties.id"))  # If from landowner
    
    # Documents
    offer_letter_id = Column(String, ForeignKey("documents.id"))
    response_document_id = Column(String, ForeignKey("documents.id"))
    
    # Outcome
    response_notes = Column(Text)
    
    # Metadata
    metadata_json = Column(JSON, default=dict)
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaymentStatus(str, PyEnum):
    """Payment status per Agreement Section 3.2(f)."""
    NOT_STARTED = "not_started"
    INITIAL_OFFER_SENT = "initial_offer_sent"
    COUNTEROFFER_RECEIVED = "counteroffer_received"
    AGREEMENT_IN_PRINCIPLE = "agreement_in_principle"
    PAYMENT_INSTRUCTION_SENT = "payment_instruction_sent"
    PAYMENT_CLEARED = "payment_cleared"


class PaymentLedger(Base):
    """Payment ledger tracking status per parcel.
    
    Agreement Reference: Section 3.2(f) - Payment ledger (status-only)
    
    Tracks payment status only - no valuation or dollar amounts computed.
    """
    __tablename__ = "payment_ledgers"
    
    id = Column(String, primary_key=True)
    parcel_id = Column(String, ForeignKey("parcels.id"), nullable=False, unique=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    
    # Status tracking (per Agreement)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.NOT_STARTED)
    
    # Current offer reference
    current_offer_id = Column(String, ForeignKey("offers.id"))
    
    # Settlement info (if applicable)
    settlement_offer_id = Column(String, ForeignKey("offers.id"))
    settlement_amount = Column(Numeric)  # Final agreed amount
    settlement_date = Column(DateTime)
    
    # Payment info
    payment_instruction_date = Column(DateTime)
    payment_cleared_date = Column(DateTime)
    payment_reference = Column(String)  # Check number, wire reference, etc.
    
    # Status history (JSON array of status changes)
    status_history = Column(JSON, default=list)
    
    # Metadata
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Alignment(Base):
    """Project alignments (routes).
    
    Agreement Reference: Section 3.2(h) - GIS alignment and parcel segmentation
    
    Represents project alignments (e.g., pipeline routes) with PostGIS geometry.
    """
    __tablename__ = "alignments"
    
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    
    # Alignment details
    name = Column(String, nullable=False)
    description = Column(Text)
    alignment_type = Column(String)  # pipeline, transmission, road, etc.
    
    # Geometry (stored as GeoJSON, use PostGIS in production)
    geometry = Column(JSON)  # LineString or MultiLineString
    
    # Attributes
    total_length_miles = Column(Numeric)
    total_parcels = Column(Integer, default=0)
    
    # Status
    status = Column(String, default="active")  # active, completed, archived
    
    # Metadata
    metadata_json = Column(JSON, default=dict)
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    segments = relationship("Segment", back_populates="alignment")


class SegmentEDStatus(str, PyEnum):
    """Per-segment ED status per Agreement Section 3.2(h)."""
    NOT_STARTED = "not_started"
    SURVEYED = "surveyed"
    NEGOTIATION = "negotiation"
    ACQUIRED = "acquired"
    CONDEMNED = "condemned"
    CLOSED = "closed"


class Segment(Base):
    """Alignment segments linked to parcels.
    
    Agreement Reference: Section 3.2(h) - per-segment ED status
    
    Links alignment segments to parcels with per-segment ED status tracking.
    """
    __tablename__ = "segments"
    
    id = Column(String, primary_key=True)
    alignment_id = Column(String, ForeignKey("alignments.id"), nullable=False)
    parcel_id = Column(String, ForeignKey("parcels.id"), nullable=False)
    
    # Segment details
    segment_number = Column(Integer)
    name = Column(String)
    
    # Geometry (portion of alignment within this parcel)
    geometry = Column(JSON)  # LineString
    
    # Measurements
    length_feet = Column(Numeric)
    width_feet = Column(Numeric)
    area_sqft = Column(Numeric)
    
    # Per-segment ED status (per Agreement)
    ed_status = Column(Enum(SegmentEDStatus), default=SegmentEDStatus.NOT_STARTED)
    
    # Acquisition type for this segment
    acquisition_type = Column(String)  # fee, permanent_easement, temporary_easement
    
    # Metadata
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    alignment = relationship("Alignment", back_populates="segments")
