"""
Chat/Messaging API Routes.

Provides threaded messaging between landowners and agents through the portal.
Supports message threads, replies, read receipts, and attachments.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Cookie
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_persona, get_current_user, get_db
from app.db import models
from app.db.models import Persona
from app.security.rbac import Action, authorize
from app.services.hashing import sha256_hex

router = APIRouter(prefix="/chat", tags=["chat"])


# =============================================================================
# Enums and Models
# =============================================================================


class MessageType(str, Enum):
    TEXT = "text"
    SYSTEM = "system"
    ATTACHMENT = "attachment"


class ThreadStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class CreateThreadRequest(BaseModel):
    parcel_id: str
    project_id: str
    subject: str
    initial_message: str


class SendMessageRequest(BaseModel):
    content: str
    message_type: str = "text"
    attachment_id: Optional[str] = None
    reply_to_id: Optional[str] = None


class ThreadResponse(BaseModel):
    thread_id: str
    parcel_id: str
    project_id: str
    subject: str
    status: str
    created_at: str
    updated_at: str
    message_count: int
    unread_count: int
    last_message: Optional[dict[str, Any]] = None
    participants: list[str]


class MessageResponse(BaseModel):
    message_id: str
    thread_id: str
    sender_persona: str
    content: str
    message_type: str
    reply_to_id: Optional[str] = None
    attachment_id: Optional[str] = None
    created_at: str
    read_at: Optional[str] = None


# In-memory store for development
_threads: dict[str, dict[str, Any]] = {}
_messages: dict[str, dict[str, Any]] = {}


# =============================================================================
# Thread Endpoints
# =============================================================================


@router.post("/threads")
def create_thread(
    payload: CreateThreadRequest,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Create a new message thread for a parcel.
    
    Threads are tied to parcels and support communication
    between landowners and agents/counsel.
    """
    authorize(persona, "communication", Action.WRITE)
    
    thread_id = f"THR-{uuid4().hex[:12].upper()}"
    message_id = f"MSG-{uuid4().hex[:12].upper()}"
    now = datetime.utcnow()
    
    # Create thread
    thread = {
        "id": thread_id,
        "parcel_id": payload.parcel_id,
        "project_id": payload.project_id,
        "subject": payload.subject,
        "status": ThreadStatus.OPEN.value,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
        "created_by": persona.value,
        "participants": [persona.value],
        "message_ids": [message_id],
    }
    _threads[thread_id] = thread
    
    # Create initial message
    message = {
        "id": message_id,
        "thread_id": thread_id,
        "sender_persona": persona.value,
        "sender_user_id": getattr(user, "id", None),
        "content": payload.initial_message,
        "message_type": MessageType.TEXT.value,
        "reply_to_id": None,
        "attachment_id": None,
        "created_at": now.isoformat() + "Z",
        "read_by": [persona.value],
    }
    _messages[message_id] = message
    
    # Persist to DB
    try:
        chat_thread = models.ChatThread(
            id=thread_id,
            parcel_id=payload.parcel_id,
            project_id=payload.project_id,
            subject=payload.subject,
            status=ThreadStatus.OPEN.value,
            created_by=getattr(user, "id", None),
            created_by_persona=persona,
            participants_json=[persona.value],
        )
        db.add(chat_thread)
        
        chat_message = models.ChatMessage(
            id=message_id,
            thread_id=thread_id,
            sender_user_id=getattr(user, "id", None),
            sender_persona=persona,
            content=payload.initial_message,
            message_type=MessageType.TEXT.value,
        )
        db.add(chat_message)
        
        # Audit log
        db.add(
            models.AuditEvent(
                id=str(uuid4()),
                user_id=getattr(user, "id", None),
                actor_persona=persona,
                action="chat.thread.create",
                resource="chat_thread",
                payload={
                    "thread_id": thread_id,
                    "parcel_id": payload.parcel_id,
                    "subject": payload.subject,
                },
                hash=sha256_hex({"thread_id": thread_id, "action": "create"}),
            )
        )
        
        db.commit()
    except Exception:
        db.rollback()
    
    return {
        "thread_id": thread_id,
        "message_id": message_id,
        "status": "created",
        "created_at": thread["created_at"],
    }


@router.get("/threads")
def list_threads(
    parcel_id: Optional[str] = None,
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """
    List message threads with optional filters.
    """
    authorize(persona, "communication", Action.READ)
    
    # Try DB first
    try:
        query = db.query(models.ChatThread)
        
        if parcel_id:
            query = query.filter(models.ChatThread.parcel_id == parcel_id)
        if project_id:
            query = query.filter(models.ChatThread.project_id == project_id)
        if status:
            query = query.filter(models.ChatThread.status == status)
        
        threads = query.order_by(models.ChatThread.updated_at.desc()).limit(50).all()
        
        items = []
        for t in threads:
            # Get message count
            msg_count = db.query(models.ChatMessage).filter(
                models.ChatMessage.thread_id == t.id
            ).count()
            
            # Get last message
            last_msg = db.query(models.ChatMessage).filter(
                models.ChatMessage.thread_id == t.id
            ).order_by(models.ChatMessage.created_at.desc()).first()
            
            items.append({
                "thread_id": t.id,
                "parcel_id": t.parcel_id,
                "project_id": t.project_id,
                "subject": t.subject,
                "status": t.status,
                "created_at": t.created_at.isoformat() + "Z" if t.created_at else None,
                "updated_at": t.updated_at.isoformat() + "Z" if t.updated_at else None,
                "message_count": msg_count,
                "last_message": {
                    "content": last_msg.content[:100] + "..." if len(last_msg.content) > 100 else last_msg.content,
                    "sender_persona": last_msg.sender_persona.value if last_msg.sender_persona else None,
                    "created_at": last_msg.created_at.isoformat() + "Z" if last_msg.created_at else None,
                } if last_msg else None,
                "participants": t.participants_json or [],
            })
        
        return {"threads": items, "count": len(items)}
    except Exception:
        pass
    
    # Fall back to in-memory
    items = []
    for thread_id, t in _threads.items():
        if parcel_id and t.get("parcel_id") != parcel_id:
            continue
        if project_id and t.get("project_id") != project_id:
            continue
        if status and t.get("status") != status:
            continue
        
        msg_ids = t.get("message_ids", [])
        last_msg = _messages.get(msg_ids[-1]) if msg_ids else None
        
        items.append({
            "thread_id": t["id"],
            "parcel_id": t["parcel_id"],
            "project_id": t["project_id"],
            "subject": t["subject"],
            "status": t["status"],
            "created_at": t["created_at"],
            "updated_at": t["updated_at"],
            "message_count": len(msg_ids),
            "last_message": {
                "content": last_msg["content"][:100] if last_msg else None,
                "sender_persona": last_msg["sender_persona"] if last_msg else None,
                "created_at": last_msg["created_at"] if last_msg else None,
            } if last_msg else None,
            "participants": t.get("participants", []),
        })
    
    return {"threads": items, "count": len(items)}


@router.get("/threads/{thread_id}")
def get_thread(
    thread_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """
    Get a specific thread with all messages.
    """
    authorize(persona, "communication", Action.READ)
    
    # Try DB first
    try:
        thread = db.get(models.ChatThread, thread_id)
        if thread:
            messages = db.query(models.ChatMessage).filter(
                models.ChatMessage.thread_id == thread_id
            ).order_by(models.ChatMessage.created_at.asc()).all()
            
            return {
                "thread_id": thread.id,
                "parcel_id": thread.parcel_id,
                "project_id": thread.project_id,
                "subject": thread.subject,
                "status": thread.status,
                "created_at": thread.created_at.isoformat() + "Z" if thread.created_at else None,
                "updated_at": thread.updated_at.isoformat() + "Z" if thread.updated_at else None,
                "participants": thread.participants_json or [],
                "messages": [
                    {
                        "message_id": m.id,
                        "sender_persona": m.sender_persona.value if m.sender_persona else None,
                        "content": m.content,
                        "message_type": m.message_type,
                        "reply_to_id": m.reply_to_id,
                        "attachment_id": m.attachment_id,
                        "created_at": m.created_at.isoformat() + "Z" if m.created_at else None,
                        "read_at": m.read_at.isoformat() + "Z" if m.read_at else None,
                    }
                    for m in messages
                ],
            }
    except Exception:
        pass
    
    # Fall back to in-memory
    if thread_id not in _threads:
        raise HTTPException(status_code=404, detail="thread_not_found")
    
    thread = _threads[thread_id]
    messages = [_messages[mid] for mid in thread.get("message_ids", []) if mid in _messages]
    
    return {
        "thread_id": thread["id"],
        "parcel_id": thread["parcel_id"],
        "project_id": thread["project_id"],
        "subject": thread["subject"],
        "status": thread["status"],
        "created_at": thread["created_at"],
        "updated_at": thread["updated_at"],
        "participants": thread.get("participants", []),
        "messages": [
            {
                "message_id": m["id"],
                "sender_persona": m["sender_persona"],
                "content": m["content"],
                "message_type": m["message_type"],
                "reply_to_id": m.get("reply_to_id"),
                "attachment_id": m.get("attachment_id"),
                "created_at": m["created_at"],
                "read_at": None,
            }
            for m in messages
        ],
    }


# =============================================================================
# Message Endpoints
# =============================================================================


@router.post("/threads/{thread_id}/messages")
def send_message(
    thread_id: str,
    payload: SendMessageRequest,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Send a message to a thread.
    
    Supports replies and attachments.
    """
    authorize(persona, "communication", Action.WRITE)
    
    message_id = f"MSG-{uuid4().hex[:12].upper()}"
    now = datetime.utcnow()
    
    # Validate thread exists
    thread = _threads.get(thread_id)
    db_thread = None
    try:
        db_thread = db.get(models.ChatThread, thread_id)
    except Exception:
        pass
    
    if not thread and not db_thread:
        raise HTTPException(status_code=404, detail="thread_not_found")
    
    # Create message
    message = {
        "id": message_id,
        "thread_id": thread_id,
        "sender_persona": persona.value,
        "sender_user_id": getattr(user, "id", None),
        "content": payload.content,
        "message_type": payload.message_type,
        "reply_to_id": payload.reply_to_id,
        "attachment_id": payload.attachment_id,
        "created_at": now.isoformat() + "Z",
        "read_by": [persona.value],
    }
    _messages[message_id] = message
    
    # Update thread
    if thread:
        thread["message_ids"].append(message_id)
        thread["updated_at"] = now.isoformat() + "Z"
        if persona.value not in thread["participants"]:
            thread["participants"].append(persona.value)
    
    # Persist to DB
    try:
        chat_message = models.ChatMessage(
            id=message_id,
            thread_id=thread_id,
            sender_user_id=getattr(user, "id", None),
            sender_persona=persona,
            content=payload.content,
            message_type=payload.message_type,
            reply_to_id=payload.reply_to_id,
            attachment_id=payload.attachment_id,
        )
        db.add(chat_message)
        
        if db_thread:
            db_thread.updated_at = now
            if persona.value not in (db_thread.participants_json or []):
                db_thread.participants_json = (db_thread.participants_json or []) + [persona.value]
        
        # Audit log
        db.add(
            models.AuditEvent(
                id=str(uuid4()),
                user_id=getattr(user, "id", None),
                actor_persona=persona,
                action="chat.message.send",
                resource="chat_message",
                payload={
                    "message_id": message_id,
                    "thread_id": thread_id,
                    "reply_to_id": payload.reply_to_id,
                },
                hash=sha256_hex({"message_id": message_id, "action": "send"}),
            )
        )
        
        db.commit()
    except Exception:
        db.rollback()
    
    return {
        "message_id": message_id,
        "thread_id": thread_id,
        "status": "sent",
        "created_at": message["created_at"],
    }


@router.post("/threads/{thread_id}/messages/{message_id}/read")
def mark_message_read(
    thread_id: str,
    message_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """
    Mark a message as read by the current persona.
    """
    authorize(persona, "communication", Action.READ)
    
    now = datetime.utcnow()
    
    # Update in-memory
    if message_id in _messages:
        if persona.value not in _messages[message_id].get("read_by", []):
            _messages[message_id].setdefault("read_by", []).append(persona.value)
    
    # Update in DB
    try:
        message = db.get(models.ChatMessage, message_id)
        if message and not message.read_at:
            message.read_at = now
            message.read_by_persona = persona
            db.commit()
    except Exception:
        db.rollback()
    
    return {"status": "marked_read", "message_id": message_id}


@router.post("/threads/{thread_id}/read-all")
def mark_thread_read(
    thread_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """
    Mark all messages in a thread as read.
    """
    authorize(persona, "communication", Action.READ)
    
    now = datetime.utcnow()
    marked_count = 0
    
    # Update in-memory
    if thread_id in _threads:
        for mid in _threads[thread_id].get("message_ids", []):
            if mid in _messages and persona.value not in _messages[mid].get("read_by", []):
                _messages[mid].setdefault("read_by", []).append(persona.value)
                marked_count += 1
    
    # Update in DB
    try:
        messages = db.query(models.ChatMessage).filter(
            models.ChatMessage.thread_id == thread_id,
            models.ChatMessage.read_at.is_(None),
        ).all()
        
        for m in messages:
            m.read_at = now
            m.read_by_persona = persona
            marked_count += 1
        
        db.commit()
    except Exception:
        db.rollback()
    
    return {"status": "marked_read", "thread_id": thread_id, "marked_count": marked_count}


# =============================================================================
# Thread Management
# =============================================================================


@router.put("/threads/{thread_id}/status")
def update_thread_status(
    thread_id: str,
    status: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Update thread status (open, resolved, archived).
    """
    authorize(persona, "communication", Action.WRITE)
    
    valid_statuses = [s.value for s in ThreadStatus]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    now = datetime.utcnow()
    
    # Update in-memory
    if thread_id in _threads:
        _threads[thread_id]["status"] = status
        _threads[thread_id]["updated_at"] = now.isoformat() + "Z"
    
    # Update in DB
    try:
        thread = db.get(models.ChatThread, thread_id)
        if thread:
            old_status = thread.status
            thread.status = status
            thread.updated_at = now
            
            # Add system message
            system_msg_id = f"MSG-{uuid4().hex[:12].upper()}"
            system_message = models.ChatMessage(
                id=system_msg_id,
                thread_id=thread_id,
                sender_persona=Persona.SYSTEM,
                content=f"Thread status changed from {old_status} to {status}",
                message_type=MessageType.SYSTEM.value,
            )
            db.add(system_message)
            
            # Audit log
            db.add(
                models.AuditEvent(
                    id=str(uuid4()),
                    user_id=getattr(user, "id", None),
                    actor_persona=persona,
                    action="chat.thread.status_change",
                    resource="chat_thread",
                    payload={
                        "thread_id": thread_id,
                        "old_status": old_status,
                        "new_status": status,
                    },
                    hash=sha256_hex({"thread_id": thread_id, "action": "status_change"}),
                )
            )
            
            db.commit()
            return {"status": "updated", "thread_id": thread_id, "new_status": status}
    except Exception:
        db.rollback()
    
    if thread_id not in _threads:
        raise HTTPException(status_code=404, detail="thread_not_found")
    
    return {"status": "updated", "thread_id": thread_id, "new_status": status}


# =============================================================================
# Portal-accessible endpoints (for landowners via session cookie)
# =============================================================================


@router.get("/portal/threads")
def portal_list_threads(
    db: Session = Depends(get_db),
    portal_session: Optional[str] = Cookie(None),
):
    """
    List threads for the current portal session (landowner view).
    
    Only returns threads for the parcel associated with the session.
    """
    if not portal_session:
        raise HTTPException(status_code=401, detail="no_session")
    
    # Validate session
    session = db.query(models.PortalSession).filter(
        models.PortalSession.session_token == portal_session,
        models.PortalSession.expires_at > datetime.utcnow(),
        models.PortalSession.revoked_at.is_(None),
    ).first()
    
    if not session:
        raise HTTPException(status_code=401, detail="invalid_or_expired_session")
    
    invite = db.get(models.PortalInvite, session.invite_id)
    if not invite or not invite.parcel_id:
        raise HTTPException(status_code=400, detail="no_parcel_associated")
    
    # Get threads for this parcel
    items = []
    for thread_id, t in _threads.items():
        if t.get("parcel_id") == invite.parcel_id:
            msg_ids = t.get("message_ids", [])
            items.append({
                "thread_id": t["id"],
                "subject": t["subject"],
                "status": t["status"],
                "message_count": len(msg_ids),
                "updated_at": t["updated_at"],
            })
    
    # Also check DB
    try:
        threads = db.query(models.ChatThread).filter(
            models.ChatThread.parcel_id == invite.parcel_id
        ).order_by(models.ChatThread.updated_at.desc()).all()
        
        for t in threads:
            if t.id not in [i["thread_id"] for i in items]:
                msg_count = db.query(models.ChatMessage).filter(
                    models.ChatMessage.thread_id == t.id
                ).count()
                items.append({
                    "thread_id": t.id,
                    "subject": t.subject,
                    "status": t.status,
                    "message_count": msg_count,
                    "updated_at": t.updated_at.isoformat() + "Z" if t.updated_at else None,
                })
    except Exception:
        pass
    
    return {"threads": items, "parcel_id": invite.parcel_id}


@router.post("/portal/threads")
def portal_create_thread(
    subject: str,
    message: str,
    db: Session = Depends(get_db),
    portal_session: Optional[str] = Cookie(None),
):
    """
    Create a thread from the landowner portal.
    """
    if not portal_session:
        raise HTTPException(status_code=401, detail="no_session")
    
    session = db.query(models.PortalSession).filter(
        models.PortalSession.session_token == portal_session,
        models.PortalSession.expires_at > datetime.utcnow(),
        models.PortalSession.revoked_at.is_(None),
    ).first()
    
    if not session:
        raise HTTPException(status_code=401, detail="invalid_or_expired_session")
    
    invite = db.get(models.PortalInvite, session.invite_id)
    if not invite:
        raise HTTPException(status_code=400, detail="invalid_invite")
    
    thread_id = f"THR-{uuid4().hex[:12].upper()}"
    message_id = f"MSG-{uuid4().hex[:12].upper()}"
    now = datetime.utcnow()
    
    # Create thread
    thread = {
        "id": thread_id,
        "parcel_id": invite.parcel_id,
        "project_id": invite.project_id,
        "subject": subject,
        "status": ThreadStatus.OPEN.value,
        "created_at": now.isoformat() + "Z",
        "updated_at": now.isoformat() + "Z",
        "created_by": Persona.LANDOWNER.value,
        "participants": [Persona.LANDOWNER.value],
        "message_ids": [message_id],
    }
    _threads[thread_id] = thread
    
    # Create message
    msg = {
        "id": message_id,
        "thread_id": thread_id,
        "sender_persona": Persona.LANDOWNER.value,
        "content": message,
        "message_type": MessageType.TEXT.value,
        "created_at": now.isoformat() + "Z",
        "read_by": [Persona.LANDOWNER.value],
    }
    _messages[message_id] = msg
    
    # Persist to DB
    try:
        chat_thread = models.ChatThread(
            id=thread_id,
            parcel_id=invite.parcel_id,
            project_id=invite.project_id,
            subject=subject,
            status=ThreadStatus.OPEN.value,
            created_by_persona=Persona.LANDOWNER,
            participants_json=[Persona.LANDOWNER.value],
        )
        db.add(chat_thread)
        
        chat_message = models.ChatMessage(
            id=message_id,
            thread_id=thread_id,
            sender_persona=Persona.LANDOWNER,
            content=message,
            message_type=MessageType.TEXT.value,
        )
        db.add(chat_message)
        
        db.add(
            models.AuditEvent(
                id=str(uuid4()),
                user_id=None,
                actor_persona=Persona.LANDOWNER,
                action="chat.thread.create",
                resource="chat_thread",
                payload={
                    "thread_id": thread_id,
                    "parcel_id": invite.parcel_id,
                    "created_via": "portal",
                },
                hash=sha256_hex({"thread_id": thread_id, "action": "portal_create"}),
            )
        )
        
        db.commit()
    except Exception:
        db.rollback()
    
    return {
        "thread_id": thread_id,
        "message_id": message_id,
        "status": "created",
    }


@router.post("/portal/threads/{thread_id}/reply")
def portal_reply_to_thread(
    thread_id: str,
    message: str,
    db: Session = Depends(get_db),
    portal_session: Optional[str] = Cookie(None),
):
    """
    Reply to a thread from the landowner portal.
    """
    if not portal_session:
        raise HTTPException(status_code=401, detail="no_session")
    
    session = db.query(models.PortalSession).filter(
        models.PortalSession.session_token == portal_session,
        models.PortalSession.expires_at > datetime.utcnow(),
        models.PortalSession.revoked_at.is_(None),
    ).first()
    
    if not session:
        raise HTTPException(status_code=401, detail="invalid_or_expired_session")
    
    # Verify thread exists and belongs to this parcel
    invite = db.get(models.PortalInvite, session.invite_id)
    thread = _threads.get(thread_id)
    
    if thread and thread.get("parcel_id") != invite.parcel_id:
        raise HTTPException(status_code=403, detail="thread_not_accessible")
    
    message_id = f"MSG-{uuid4().hex[:12].upper()}"
    now = datetime.utcnow()
    
    msg = {
        "id": message_id,
        "thread_id": thread_id,
        "sender_persona": Persona.LANDOWNER.value,
        "content": message,
        "message_type": MessageType.TEXT.value,
        "created_at": now.isoformat() + "Z",
        "read_by": [Persona.LANDOWNER.value],
    }
    _messages[message_id] = msg
    
    if thread:
        thread["message_ids"].append(message_id)
        thread["updated_at"] = now.isoformat() + "Z"
    
    # Persist to DB
    try:
        chat_message = models.ChatMessage(
            id=message_id,
            thread_id=thread_id,
            sender_persona=Persona.LANDOWNER,
            content=message,
            message_type=MessageType.TEXT.value,
        )
        db.add(chat_message)
        
        db_thread = db.get(models.ChatThread, thread_id)
        if db_thread:
            db_thread.updated_at = now
        
        db.commit()
    except Exception:
        db.rollback()
    
    return {
        "message_id": message_id,
        "thread_id": thread_id,
        "status": "sent",
    }
