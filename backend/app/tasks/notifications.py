"""Celery tasks for notifications.

These tasks handle:
- Email notifications via SendGrid
- SMS notifications via Twilio
- Deadline digest notifications
- Escalation alerts
"""

from celery import shared_task
from typing import Any
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_deadline_digest() -> dict[str, Any]:
    """Send daily deadline digest to relevant users.
    
    Scheduled task that runs at 8 AM to send a summary
    of upcoming deadlines to counsel and agents.
    
    Returns:
        Summary of notifications sent
    """
    logger.info("Sending daily deadline digest")
    
    try:
        from app.services.notifications import preview_or_send
        from app.db.session import get_db_session
        from app.db.models import Deadline, Project, User
        from datetime import datetime, timedelta
        
        # TODO: Implement full digest logic
        # 1. Query upcoming deadlines (next 7 days)
        # 2. Group by project and user
        # 3. Generate digest email for each user
        # 4. Send via notification service
        
        return {
            "emails_sent": 0,
            "sms_sent": 0,
            "users_notified": 0,
        }
        
    except Exception as exc:
        logger.error(f"Deadline digest failed: {exc}")
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_notification(
    self,
    recipient_email: str,
    template_id: str,
    variables: dict[str, Any],
    subject: str | None = None
) -> dict[str, Any]:
    """Send an email notification.
    
    Args:
        recipient_email: Recipient email address
        template_id: Notification template ID
        variables: Template variables
        subject: Optional subject override
        
    Returns:
        Send result
    """
    try:
        from app.services.notifications import preview_or_send
        
        result = preview_or_send(
            channel="email",
            recipient=recipient_email,
            template_id=template_id,
            variables=variables,
            subject=subject,
        )
        
        return {
            "success": result.get("status") == "sent",
            "channel": "email",
            "recipient": recipient_email,
        }
        
    except Exception as exc:
        logger.error(f"Email send failed to {recipient_email}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_sms_notification(
    self,
    recipient_phone: str,
    message: str
) -> dict[str, Any]:
    """Send an SMS notification.
    
    Args:
        recipient_phone: Recipient phone number
        message: SMS message text
        
    Returns:
        Send result
    """
    try:
        from app.services.notifications import preview_or_send
        
        result = preview_or_send(
            channel="sms",
            recipient=recipient_phone,
            message=message,
        )
        
        return {
            "success": result.get("status") == "sent",
            "channel": "sms",
            "recipient": recipient_phone,
        }
        
    except Exception as exc:
        logger.error(f"SMS send failed to {recipient_phone}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_escalation_alert(
    self,
    escalation_id: str,
    recipient_ids: list[str],
    priority: str = "medium"
) -> dict[str, Any]:
    """Send escalation alerts to assigned reviewers.
    
    Multi-channel notification based on priority:
    - Low/Medium: Email only
    - High: Email + optional SMS
    - Critical: Email + SMS (immediate)
    
    Args:
        escalation_id: Escalation request ID
        recipient_ids: User IDs to notify
        priority: Escalation priority
        
    Returns:
        Notification results
    """
    logger.info(f"Sending escalation alerts for {escalation_id} ({priority})")
    
    try:
        from app.services.notifications import preview_or_send
        from app.db.session import SessionLocal
        from app.db.models import User, EscalationRequest, AIDecision
        from sqlalchemy import select
        
        emails_sent = 0
        sms_sent = 0
        errors = []
        
        db = SessionLocal()
        try:
            # Fetch escalation details
            esc_result = db.execute(
                select(EscalationRequest).where(EscalationRequest.id == escalation_id)
            )
            escalation = esc_result.scalar_one_or_none()
            
            if not escalation:
                logger.warning(f"Escalation {escalation_id} not found")
                return {"escalation_id": escalation_id, "error": "not_found"}
            
            # Fetch related AI decision for context
            decision_result = db.execute(
                select(AIDecision).where(AIDecision.id == escalation.ai_decision_id)
            )
            decision = decision_result.scalar_one_or_none()
            
            # Build notification content
            subject = f"[{priority.upper()}] AI Decision Requires Review"
            
            body_parts = [
                f"An AI agent decision requires your review.",
                "",
                f"Escalation ID: {escalation_id}",
                f"Reason: {escalation.reason}",
                f"Priority: {priority.upper()}",
            ]
            
            if decision:
                body_parts.extend([
                    "",
                    f"Agent: {decision.agent_type}",
                    f"Confidence: {float(decision.confidence):.0%}",
                ])
                if decision.explanation:
                    body_parts.extend(["", f"Details: {decision.explanation[:200]}"])
            
            body_parts.extend([
                "",
                "Please review and take action in the LandRight platform.",
            ])
            
            body = "\n".join(body_parts)
            
            # Send to each recipient
            for recipient_id in recipient_ids:
                user_result = db.execute(
                    select(User).where(User.id == recipient_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    continue
                
                # Send email
                if user.email:
                    try:
                        result = preview_or_send(
                            channel="email",
                            recipient=user.email,
                            template_id="escalation_alert",
                            variables={
                                "escalation_id": escalation_id,
                                "priority": priority,
                                "reason": escalation.reason,
                                "agent_type": decision.agent_type if decision else "Unknown",
                                "user_name": user.full_name or user.email,
                            },
                            subject=subject,
                        )
                        if result.get("status") in ["sent", "preview"]:
                            emails_sent += 1
                    except Exception as e:
                        errors.append(f"Email to {user.email}: {e}")
                
                # Send SMS for high/critical priority
                if priority in ["high", "critical"]:
                    phone = getattr(user, 'phone', None)
                    if phone:
                        try:
                            sms_body = f"LandRight: {priority.upper()} escalation requires review. ID: {escalation_id[:8]}. Check your email for details."
                            result = preview_or_send(
                                channel="sms",
                                recipient=phone,
                                message=sms_body,
                            )
                            if result.get("status") in ["sent", "preview"]:
                                sms_sent += 1
                        except Exception as e:
                            errors.append(f"SMS to {phone}: {e}")
            
        finally:
            db.close()
        
        logger.info(
            f"Escalation alert sent: {emails_sent} emails, {sms_sent} SMS, {len(errors)} errors"
        )
        
        return {
            "escalation_id": escalation_id,
            "emails_sent": emails_sent,
            "sms_sent": sms_sent,
            "total_recipients": len(recipient_ids),
            "errors": errors if errors else None,
            "priority": priority,
        }
        
    except Exception as exc:
        logger.error(f"Escalation alert failed for {escalation_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True)
def send_compliance_violation_alert(
    self,
    case_id: str,
    violation_type: str,
    details: dict[str, Any]
) -> dict[str, Any]:
    """Send compliance violation alert to counsel.
    
    Args:
        case_id: Affected case ID
        violation_type: Type of violation
        details: Violation details
        
    Returns:
        Notification result
    """
    try:
        # TODO: Implement violation alert
        # 1. Determine severity
        # 2. Find responsible counsel
        # 3. Send multi-channel alert
        
        return {
            "case_id": case_id,
            "violation_type": violation_type,
            "alerts_sent": 0,
        }
        
    except Exception as exc:
        logger.error(f"Compliance violation alert failed for case {case_id}: {exc}")
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_document_ready_notification(
    self,
    document_id: str,
    reviewer_ids: list[str],
    document_type: str = "document",
    project_id: str = None
) -> dict[str, Any]:
    """Notify reviewers that a document is ready for review.
    
    Sends email notifications to counsel when AI-generated
    documents require human review before filing.
    
    Args:
        document_id: Document awaiting review
        reviewer_ids: Users to notify
        document_type: Type of document for context
        project_id: Related project ID
        
    Returns:
        Notification results
    """
    logger.info(f"Sending document ready notification for {document_id}")
    
    try:
        from app.services.notifications import preview_or_send
        from app.db.session import SessionLocal
        from app.db.models import User, Document
        from sqlalchemy import select
        
        emails_sent = 0
        
        db = SessionLocal()
        try:
            # Fetch document details
            doc_result = db.execute(
                select(Document).where(Document.id == document_id)
            )
            document = doc_result.scalar_one_or_none()
            
            doc_name = document.doc_type if document else document_type
            
            subject = f"Document Ready for Review: {doc_name}"
            
            for recipient_id in reviewer_ids:
                user_result = db.execute(
                    select(User).where(User.id == recipient_id)
                )
                user = user_result.scalar_one_or_none()
                
                if user and user.email:
                    try:
                        result = preview_or_send(
                            channel="email",
                            recipient=user.email,
                            template_id="document_review",
                            variables={
                                "document_id": document_id,
                                "document_type": doc_name,
                                "project_id": project_id,
                                "user_name": user.full_name or user.email,
                            },
                            subject=subject,
                        )
                        if result.get("status") in ["sent", "preview"]:
                            emails_sent += 1
                    except Exception as e:
                        logger.warning(f"Failed to notify {user.email}: {e}")
            
        finally:
            db.close()
        
        return {
            "document_id": document_id,
            "reviewers_notified": emails_sent,
            "total_recipients": len(reviewer_ids),
        }
        
    except Exception as exc:
        logger.error(f"Document ready notification failed for {document_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_deadline_reminder(
    self,
    deadline_id: str,
    days_remaining: int,
    recipient_ids: list[str]
) -> dict[str, Any]:
    """Send deadline reminder notifications.
    
    Triggered by FilingAgent when deadlines are approaching
    at configured intervals (7, 3, 1 days).
    
    Args:
        deadline_id: Deadline ID
        days_remaining: Days until deadline
        recipient_ids: Users to notify
        
    Returns:
        Notification results
    """
    logger.info(f"Sending deadline reminder for {deadline_id} ({days_remaining} days)")
    
    try:
        from app.services.notifications import preview_or_send
        from app.db.session import SessionLocal
        from app.db.models import User, Deadline
        from sqlalchemy import select
        
        emails_sent = 0
        sms_sent = 0
        
        db = SessionLocal()
        try:
            # Fetch deadline details
            dl_result = db.execute(
                select(Deadline).where(Deadline.id == deadline_id)
            )
            deadline = dl_result.scalar_one_or_none()
            
            if not deadline:
                return {"deadline_id": deadline_id, "error": "not_found"}
            
            urgency = "urgent" if days_remaining <= 1 else "warning" if days_remaining <= 3 else "reminder"
            subject = f"[{urgency.upper()}] Deadline in {days_remaining} day(s): {deadline.title}"
            
            for recipient_id in recipient_ids:
                user_result = db.execute(
                    select(User).where(User.id == recipient_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    continue
                
                # Send email
                if user.email:
                    try:
                        result = preview_or_send(
                            channel="email",
                            recipient=user.email,
                            template_id="deadline_reminder",
                            variables={
                                "deadline_title": deadline.title,
                                "days_remaining": days_remaining,
                                "due_date": deadline.due_at.strftime("%B %d, %Y"),
                                "project_id": deadline.project_id,
                                "urgency": urgency,
                            },
                            subject=subject,
                        )
                        if result.get("status") in ["sent", "preview"]:
                            emails_sent += 1
                    except Exception as e:
                        logger.warning(f"Email failed for {user.email}: {e}")
                
                # Send SMS for urgent deadlines (1 day or less)
                if days_remaining <= 1:
                    phone = getattr(user, 'phone', None)
                    if phone:
                        try:
                            sms_body = f"LandRight URGENT: '{deadline.title}' due in {days_remaining} day(s). Take action now."
                            result = preview_or_send(
                                channel="sms",
                                recipient=phone,
                                message=sms_body,
                            )
                            if result.get("status") in ["sent", "preview"]:
                                sms_sent += 1
                        except Exception as e:
                            logger.warning(f"SMS failed for {phone}: {e}")
            
        finally:
            db.close()
        
        return {
            "deadline_id": deadline_id,
            "days_remaining": days_remaining,
            "emails_sent": emails_sent,
            "sms_sent": sms_sent,
        }
        
    except Exception as exc:
        logger.error(f"Deadline reminder failed for {deadline_id}: {exc}")
        raise self.retry(exc=exc)
