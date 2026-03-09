"""Filing Agent for deadline monitoring and e-filing.

This agent handles:
- Monitoring all case deadlines
- Sending reminder notifications
- E-filing court documents
- Recording deeds with county clerks
- Interpreting filing errors

It integrates with:
- Deadline service for deadline tracking
- Court e-filing systems (Tyler Odyssey, File & Serve)
- County recording systems (Simplifile)
- Notification service for reminders
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

from app.agents.base import BaseAgent, AgentContext, AgentResult, AgentType

logger = logging.getLogger(__name__)


# Prompt for interpreting filing errors
FILING_ERROR_PROMPT = """Interpret this court e-filing error.

Error Response:
{error_response}

Document Type: {document_type}
Court: {court_name}
Filing Date: {filing_date}

Common Issues:
- Format violations (margins, font, page limits)
- Missing required fields or signatures
- Filing fee issues
- Service defects
- Case number errors

Determine:
1. What is the root cause of the rejection?
2. What specific corrections are needed?
3. Can the document be re-filed after corrections?
4. How urgent is this correction?

Return JSON:
{{
    "error_type": "format|content|fee|service|technical",
    "root_cause": "description of the issue",
    "corrections_needed": ["specific correction 1", "correction 2"],
    "can_refile": true/false,
    "urgency": "low|medium|high|critical",
    "suggested_actions": ["action 1", "action 2"],
    "estimated_correction_time": "1-2 hours|same day|1-2 days"
}}
"""


@dataclass
class DeadlineCheck:
    """Result of checking a deadline."""
    deadline_id: str
    title: str
    due_at: datetime
    days_remaining: int
    status: str  # ok, warning, critical, missed
    action_taken: str  # none, reminder, escalate
    notification_sent: bool = False


@dataclass
class FilingResult:
    """Result of an e-filing attempt."""
    document_id: str
    court_id: str
    accepted: bool
    confirmation_number: Optional[str] = None
    filing_date: Optional[datetime] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    interpretation: Optional[dict[str, Any]] = None


class FilingAgent(BaseAgent):
    """Agent for deadline monitoring and e-filing.
    
    Responsibilities:
    - Monitor deadlines across all cases
    - Send reminders at configurable intervals
    - Handle court e-filing
    - Record deeds with county clerks
    - Interpret and respond to filing errors
    
    Escalation triggers:
    - Missed deadlines
    - Filing rejections
    - Court system errors
    """
    
    agent_type = AgentType.FILING
    confidence_threshold = 0.90  # High threshold for legal filings
    
    # Reminder intervals (days before deadline)
    REMINDER_INTERVALS = [7, 3, 1]
    
    def __init__(self, db_session=None, confidence_threshold: float = None):
        """Initialize the filing agent.
        
        Args:
            db_session: Database session
            confidence_threshold: Override default threshold
        """
        super().__init__(confidence_threshold)
        self.db = db_session
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute filing action based on context.
        
        Args:
            context: Agent context with action details
            
        Returns:
            AgentResult with action outcome
        """
        start_time = datetime.utcnow()
        
        try:
            action = context.action or "check_deadlines"
            
            if action == "check_deadlines":
                results = await self.check_deadlines()
                return self._build_deadline_result(results, start_time)
            
            elif action == "file_document":
                if not context.document_id or not context.court_id:
                    return AgentResult.failure_result(
                        error="document_id and court_id required for filing",
                        error_code="MISSING_PARAMS",
                    )
                result = await self.file_document(
                    context.document_id,
                    context.court_id,
                    context.case_number,
                )
                return self._build_filing_result(result, start_time)
            
            elif action == "record_deed":
                if not context.document_id:
                    return AgentResult.failure_result(
                        error="document_id required for recording",
                        error_code="MISSING_PARAMS",
                    )
                result = await self.record_deed(
                    context.document_id,
                    context.payload.get("county_fips") if context.payload else None,
                )
                return self._build_filing_result(result, start_time)
            
            else:
                return AgentResult.failure_result(
                    error=f"Unknown action: {action}",
                    error_code="UNKNOWN_ACTION",
                )
            
        except Exception as e:
            self.logger.error(f"Filing agent execution failed: {e}", exc_info=True)
            return AgentResult.failure_result(
                error=str(e),
                error_code="FILING_ERROR",
            )
    
    async def check_deadlines(self, days_ahead: int = 7) -> list[DeadlineCheck]:
        """Check all upcoming deadlines.
        
        Args:
            days_ahead: How many days ahead to check
            
        Returns:
            List of deadline check results
        """
        results = []
        now = datetime.utcnow()
        
        # Get upcoming deadlines
        deadlines = await self._get_upcoming_deadlines(days_ahead)
        
        for deadline in deadlines:
            due_at = deadline.get("due_at")
            if isinstance(due_at, str):
                due_at = datetime.fromisoformat(due_at)
            
            days_remaining = (due_at - now).days
            
            # Determine status
            if days_remaining < 0:
                status = "missed"
                action = "escalate"
            elif days_remaining == 0:
                status = "critical"
                action = "escalate"
            elif days_remaining <= 3:
                status = "warning"
                action = "reminder"
            else:
                status = "ok"
                action = "none"
            
            # Take action
            notification_sent = False
            if action == "escalate":
                await self.escalate_missed_deadline(deadline.get("id"))
            elif action == "reminder" and days_remaining in self.REMINDER_INTERVALS:
                await self.send_reminder(deadline.get("id"), days_remaining, [])
                notification_sent = True
            
            results.append(DeadlineCheck(
                deadline_id=deadline.get("id", ""),
                title=deadline.get("title", "Unknown"),
                due_at=due_at,
                days_remaining=days_remaining,
                status=status,
                action_taken=action,
                notification_sent=notification_sent,
            ))
        
        return results
    
    async def file_document(
        self,
        document_id: str,
        court_id: str,
        case_number: str = None,
    ) -> FilingResult:
        """File a document with the court.
        
        Args:
            document_id: Document to file
            court_id: Target court
            case_number: Existing case number
            
        Returns:
            Filing result
        """
        self.logger.info(f"Filing document {document_id} with court {court_id}")
        
        # Get court adapter
        adapter = self._get_filing_adapter(court_id)
        
        # Get document
        document = await self._get_document(document_id)
        if not document:
            return FilingResult(
                document_id=document_id,
                court_id=court_id,
                accepted=False,
                error_code="DOCUMENT_NOT_FOUND",
                error_message=f"Document {document_id} not found",
            )
        
        # Validate document format
        validation = await self._validate_for_court(document, court_id)
        if not validation.get("valid"):
            return FilingResult(
                document_id=document_id,
                court_id=court_id,
                accepted=False,
                error_code="VALIDATION_FAILED",
                error_message=validation.get("error", "Validation failed"),
            )
        
        # Submit filing
        try:
            result = await adapter.submit(document, case_number)
            
            if result.get("accepted"):
                await self._record_filing(document_id, result)
                return FilingResult(
                    document_id=document_id,
                    court_id=court_id,
                    accepted=True,
                    confirmation_number=result.get("confirmation_number"),
                    filing_date=datetime.utcnow(),
                )
            else:
                # Interpret error
                interpretation = await self.interpret_filing_error(
                    result,
                    document.get("doc_type", ""),
                    court_id,
                )
                return FilingResult(
                    document_id=document_id,
                    court_id=court_id,
                    accepted=False,
                    error_code=result.get("error_code"),
                    error_message=result.get("error_message"),
                    interpretation=interpretation,
                )
                
        except Exception as e:
            self.logger.error(f"Filing failed: {e}")
            return FilingResult(
                document_id=document_id,
                court_id=court_id,
                accepted=False,
                error_code="FILING_EXCEPTION",
                error_message=str(e),
            )
    
    async def record_deed(
        self,
        document_id: str,
        county_fips: str,
    ) -> FilingResult:
        """Record a deed with the county clerk.
        
        Args:
            document_id: Deed document to record
            county_fips: County FIPS code
            
        Returns:
            Recording result
        """
        self.logger.info(f"Recording deed {document_id} in county {county_fips}")
        
        # Get document
        document = await self._get_document(document_id)
        if not document:
            return FilingResult(
                document_id=document_id,
                court_id=county_fips,
                accepted=False,
                error_code="DOCUMENT_NOT_FOUND",
                error_message=f"Document {document_id} not found",
            )
        
        # TODO: Integrate with Simplifile or county e-recording
        # For now, return mock success
        return FilingResult(
            document_id=document_id,
            court_id=county_fips,
            accepted=True,
            confirmation_number=f"REC-{uuid4().hex[:8].upper()}",
            filing_date=datetime.utcnow(),
        )
    
    async def send_reminder(
        self,
        deadline_id: str,
        days_remaining: int,
        recipient_ids: list[str] = None,
    ) -> dict[str, Any]:
        """Send deadline reminder notification.
        
        Queues a Celery task to send multi-channel notifications
        to relevant users about approaching deadlines.
        
        Args:
            deadline_id: Deadline to remind about
            days_remaining: Days until deadline
            recipient_ids: Users to notify (auto-determined if not provided)
            
        Returns:
            Notification result
        """
        # Get deadline details
        deadline = await self._get_deadline(deadline_id)
        if not deadline:
            return {"success": False, "error": "Deadline not found"}
        
        # Auto-determine recipients if not provided
        if not recipient_ids:
            recipient_ids = await self._get_deadline_recipients(deadline)
        
        if not recipient_ids:
            self.logger.warning(f"No recipients for deadline {deadline_id}")
            return {"success": False, "error": "No recipients found"}
        
        # Queue notification task
        try:
            from app.tasks.notifications import send_deadline_reminder
            
            send_deadline_reminder.delay(
                deadline_id=deadline_id,
                days_remaining=days_remaining,
                recipient_ids=recipient_ids,
            )
            
            self.logger.info(
                f"Queued deadline reminder for {deadline_id}: {days_remaining} days, {len(recipient_ids)} recipients"
            )
            
            return {
                "success": True,
                "deadline_id": deadline_id,
                "days_remaining": days_remaining,
                "recipients_notified": len(recipient_ids),
                "channels": ["email", "sms"] if days_remaining <= 1 else ["email"],
            }
            
        except Exception as e:
            self.logger.error(f"Failed to queue reminder: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_deadline_recipients(self, deadline: dict[str, Any]) -> list[str]:
        """Get recipients for a deadline notification.
        
        Returns counsel and agents assigned to the project/parcel.
        
        Args:
            deadline: Deadline data
            
        Returns:
            List of user IDs
        """
        if not self.db:
            return []
        
        try:
            from app.db.models import User, Persona
            from sqlalchemy import select
            
            # Get counsel users (always notified)
            result = await self.db.execute(
                select(User).where(User.persona.in_([
                    Persona.IN_HOUSE_COUNSEL,
                    Persona.LAND_AGENT,
                ]))
            )
            users = result.scalars().all()
            return [u.id for u in users]
            
        except Exception as e:
            self.logger.warning(f"Failed to get deadline recipients: {e}")
            return []
    
    async def escalate_missed_deadline(self, deadline_id: str) -> dict[str, Any]:
        """Create escalation for missed deadline.
        
        Args:
            deadline_id: Missed deadline
            
        Returns:
            Escalation result
        """
        deadline = await self._get_deadline(deadline_id)
        if not deadline:
            return {"success": False, "error": "Deadline not found"}
        
        escalation_id = str(uuid4())
        
        # Create escalation request
        if self.db:
            try:
                from app.db.models import EscalationRequest, AIDecision
                
                # Create AI decision record
                decision_id = str(uuid4())
                ai_decision = AIDecision(
                    id=decision_id,
                    agent_type="FilingAgent",
                    project_id=deadline.get("project_id"),
                    parcel_id=deadline.get("parcel_id"),
                    context_hash="",
                    result_data={"deadline_id": deadline_id, "status": "missed"},
                    confidence=1.0,
                    flags=["deadline_missed"],
                    explanation=f"Deadline '{deadline.get('title')}' was missed",
                    occurred_at=datetime.utcnow(),
                    hash="",
                )
                self.db.add(ai_decision)
                
                escalation = EscalationRequest(
                    id=escalation_id,
                    ai_decision_id=decision_id,
                    reason="deadline_missed",
                    priority="critical",
                    status="open",
                    created_at=datetime.utcnow(),
                )
                self.db.add(escalation)
                await self.db.commit()
                
            except Exception as e:
                self.logger.error(f"Failed to create escalation: {e}")
        
        return {
            "success": True,
            "escalation_id": escalation_id,
            "deadline_id": deadline_id,
            "priority": "critical",
        }
    
    async def interpret_filing_error(
        self,
        error_response: dict[str, Any],
        document_type: str,
        court_name: str,
    ) -> dict[str, Any]:
        """Use AI to interpret a filing error.
        
        Args:
            error_response: Error from e-filing system
            document_type: Type of document
            court_name: Court name
            
        Returns:
            Error interpretation
        """
        prompt = FILING_ERROR_PROMPT.format(
            error_response=str(error_response),
            document_type=document_type,
            court_name=court_name,
            filing_date=datetime.utcnow().isoformat(),
        )
        
        response = await self.call_ai(prompt, task_type="filing_error")
        
        if response:
            return response
        
        # Default interpretation if AI unavailable
        return {
            "error_type": "technical",
            "root_cause": error_response.get("error_message", "Unknown error"),
            "corrections_needed": ["Review error and retry"],
            "can_refile": True,
            "urgency": "medium",
            "suggested_actions": ["Review filing requirements", "Contact court clerk if needed"],
        }
    
    def _get_filing_adapter(self, court_id: str):
        """Get the e-filing adapter for a court.
        
        Args:
            court_id: Court identifier
            
        Returns:
            Filing adapter instance
        """
        # TODO: Implement actual adapters for Tyler Odyssey, File & Serve, etc.
        # For now, return a mock adapter
        return MockFilingAdapter(court_id)
    
    async def _get_upcoming_deadlines(self, days_ahead: int) -> list[dict[str, Any]]:
        """Get deadlines within the specified window.
        
        Args:
            days_ahead: Days to look ahead
            
        Returns:
            List of deadline records
        """
        if not self.db:
            # Return mock deadlines
            now = datetime.utcnow()
            return [
                {
                    "id": "dl-1",
                    "title": "Response deadline",
                    "due_at": now + timedelta(days=3),
                    "project_id": "proj-1",
                },
                {
                    "id": "dl-2",
                    "title": "Filing deadline",
                    "due_at": now + timedelta(days=7),
                    "project_id": "proj-1",
                },
            ]
        
        try:
            from app.db.models import Deadline
            from sqlalchemy import select
            
            cutoff = datetime.utcnow() + timedelta(days=days_ahead)
            
            result = await self.db.execute(
                select(Deadline).where(Deadline.due_at <= cutoff)
            )
            deadlines = result.scalars().all()
            
            return [
                {
                    "id": d.id,
                    "title": d.title,
                    "due_at": d.due_at,
                    "project_id": d.project_id,
                    "parcel_id": d.parcel_id,
                }
                for d in deadlines
            ]
            
        except Exception as e:
            self.logger.error(f"Failed to fetch deadlines: {e}")
            return []
    
    async def _get_deadline(self, deadline_id: str) -> Optional[dict[str, Any]]:
        """Get a specific deadline."""
        if not self.db:
            return {
                "id": deadline_id,
                "title": "Test deadline",
                "due_at": datetime.utcnow() + timedelta(days=1),
            }
        
        try:
            from app.db.models import Deadline
            from sqlalchemy import select
            
            result = await self.db.execute(
                select(Deadline).where(Deadline.id == deadline_id)
            )
            deadline = result.scalar_one_or_none()
            
            if deadline:
                return {
                    "id": deadline.id,
                    "title": deadline.title,
                    "due_at": deadline.due_at,
                    "project_id": deadline.project_id,
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to fetch deadline: {e}")
            return None
    
    async def _get_document(self, document_id: str) -> Optional[dict[str, Any]]:
        """Get document by ID."""
        if not self.db:
            return {"id": document_id, "doc_type": "petition"}
        
        try:
            from app.db.models import Document
            from sqlalchemy import select
            
            result = await self.db.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            
            if doc:
                return {
                    "id": doc.id,
                    "doc_type": doc.doc_type,
                    "storage_path": doc.storage_path,
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to fetch document: {e}")
            return None
    
    async def _validate_for_court(
        self,
        document: dict[str, Any],
        court_id: str,
    ) -> dict[str, Any]:
        """Validate document for court requirements."""
        # TODO: Implement court-specific validation
        return {"valid": True}
    
    async def _record_filing(
        self,
        document_id: str,
        result: dict[str, Any],
    ) -> None:
        """Record successful filing in database."""
        # TODO: Implement filing record
        pass
    
    def _build_deadline_result(
        self,
        checks: list[DeadlineCheck],
        start_time: datetime,
    ) -> AgentResult:
        """Build AgentResult from deadline checks."""
        missed = sum(1 for c in checks if c.status == "missed")
        critical = sum(1 for c in checks if c.status == "critical")
        warnings = sum(1 for c in checks if c.status == "warning")
        
        flags = []
        if missed > 0:
            flags.append("deadline_missed")
        if critical > 0:
            flags.append("critical_deadline")
        
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return AgentResult(
            success=missed == 0,
            confidence=0.95,
            data={
                "deadlines_checked": len(checks),
                "missed": missed,
                "critical": critical,
                "warnings": warnings,
                "reminders_sent": sum(1 for c in checks if c.notification_sent),
                "checks": [
                    {
                        "deadline_id": c.deadline_id,
                        "title": c.title,
                        "days_remaining": c.days_remaining,
                        "status": c.status,
                        "action_taken": c.action_taken,
                    }
                    for c in checks
                ],
            },
            flags=flags,
            requires_review=missed > 0 or critical > 0,
            audit_payload={
                "explanation": f"Checked {len(checks)} deadlines: {missed} missed, {critical} critical, {warnings} warnings",
            },
            execution_time_ms=int(execution_time),
        )
    
    def _build_filing_result(
        self,
        result: FilingResult,
        start_time: datetime,
    ) -> AgentResult:
        """Build AgentResult from filing result."""
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        flags = []
        if not result.accepted:
            flags.append("filing_rejected")
        
        return AgentResult(
            success=result.accepted,
            confidence=0.95 if result.accepted else 0.7,
            data={
                "document_id": result.document_id,
                "court_id": result.court_id,
                "accepted": result.accepted,
                "confirmation_number": result.confirmation_number,
                "filing_date": result.filing_date.isoformat() if result.filing_date else None,
                "error_code": result.error_code,
                "error_message": result.error_message,
                "interpretation": result.interpretation,
            },
            flags=flags,
            requires_review=not result.accepted,
            audit_payload={
                "explanation": f"Filing {'accepted' if result.accepted else 'rejected'}: {result.confirmation_number or result.error_message}",
            },
            execution_time_ms=int(execution_time),
        )


class MockFilingAdapter:
    """Mock filing adapter for development."""
    
    def __init__(self, court_id: str):
        self.court_id = court_id
    
    async def submit(
        self,
        document: dict[str, Any],
        case_number: str = None,
    ) -> dict[str, Any]:
        """Submit document for filing."""
        # Mock successful filing
        return {
            "accepted": True,
            "confirmation_number": f"EF-{uuid4().hex[:8].upper()}",
        }
