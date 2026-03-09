"""WebSocket endpoint for real-time notifications.

Provides real-time push notifications to connected clients for:
- Deadline alerts (approaching/overdue)
- Workflow stage changes
- AI escalations requiring review
- New offers/responses
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set, Any
import json
import logging
import asyncio
import redis
from datetime import datetime
from uuid import uuid4

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["WebSocket"])


# =============================================================================
# Connection Manager
# =============================================================================

class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        # Map of user_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Map of connection -> user_id
        self.connection_users: Dict[WebSocket, str] = {}
        # Subscriptions: user_id -> set of topics
        self.subscriptions: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
            self.subscriptions[user_id] = {"all"}  # Default subscription
        
        self.active_connections[user_id].add(websocket)
        self.connection_users[websocket] = user_id
        
        logger.info(f"WebSocket connected: user={user_id}, total_connections={self.total_connections}")
        
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "user_id": user_id,
            "subscriptions": list(self.subscriptions.get(user_id, [])),
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        user_id = self.connection_users.get(websocket)
        if user_id:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            del self.connection_users[websocket]
            logger.info(f"WebSocket disconnected: user={user_id}")
    
    async def subscribe(self, user_id: str, topics: list[str]):
        """Subscribe a user to specific notification topics."""
        if user_id in self.subscriptions:
            self.subscriptions[user_id].update(topics)
    
    async def unsubscribe(self, user_id: str, topics: list[str]):
        """Unsubscribe a user from specific topics."""
        if user_id in self.subscriptions:
            self.subscriptions[user_id] -= set(topics)
    
    async def send_personal(self, user_id: str, message: dict):
        """Send a message to a specific user."""
        connections = self.active_connections.get(user_id, set())
        for connection in list(connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id}: {e}")
                connections.discard(connection)
    
    async def broadcast(self, message: dict, topic: str = "all"):
        """Broadcast a message to all users subscribed to a topic."""
        for user_id, subs in self.subscriptions.items():
            if topic in subs or "all" in subs:
                await self.send_personal(user_id, message)
    
    async def broadcast_to_users(self, user_ids: list[str], message: dict):
        """Send a message to specific users."""
        for user_id in user_ids:
            await self.send_personal(user_id, message)
    
    @property
    def total_connections(self) -> int:
        """Total number of active connections."""
        return sum(len(conns) for conns in self.active_connections.values())
    
    @property
    def connected_users(self) -> int:
        """Number of unique connected users."""
        return len(self.active_connections)


# Global connection manager
manager = ConnectionManager()


# =============================================================================
# Notification Types
# =============================================================================

class NotificationType:
    """Notification type constants."""
    DEADLINE_ALERT = "deadline_alert"
    DEADLINE_OVERDUE = "deadline_overdue"
    WORKFLOW_CHANGE = "workflow_change"
    AI_ESCALATION = "ai_escalation"
    OFFER_RECEIVED = "offer_received"
    OFFER_RESPONSE = "offer_response"
    DOCUMENT_UPLOADED = "document_uploaded"
    CASE_UPDATE = "case_update"
    SYSTEM = "system"


async def create_notification(
    notification_type: str,
    title: str,
    message: str,
    data: dict = None,
    severity: str = "info",
    action_url: str = None,
) -> dict:
    """Create a standardized notification payload."""
    return {
        "id": str(uuid4()),
        "type": notification_type,
        "title": title,
        "message": message,
        "data": data or {},
        "severity": severity,  # info, warning, error, success
        "action_url": action_url,
        "timestamp": datetime.utcnow().isoformat(),
        "read": False,
    }


# =============================================================================
# Notification Emitters (used by other services)
# =============================================================================

async def emit_deadline_alert(
    user_ids: list[str],
    deadline_id: str,
    title: str,
    due_at: str,
    days_remaining: int,
    parcel_id: str = None,
    project_id: str = None,
):
    """Emit a deadline alert notification."""
    severity = "warning" if days_remaining <= 3 else "info"
    if days_remaining <= 0:
        severity = "error"
    
    notification = await create_notification(
        notification_type=NotificationType.DEADLINE_ALERT,
        title="Deadline Approaching" if days_remaining > 0 else "Deadline Overdue",
        message=f"{title} - {'Due in ' + str(days_remaining) + ' days' if days_remaining > 0 else 'OVERDUE'}",
        data={
            "deadline_id": deadline_id,
            "due_at": due_at,
            "days_remaining": days_remaining,
            "parcel_id": parcel_id,
            "project_id": project_id,
        },
        severity=severity,
        action_url=f"/deadlines?id={deadline_id}" if deadline_id else None,
    )
    
    await manager.broadcast_to_users(user_ids, notification)


async def emit_workflow_change(
    user_ids: list[str],
    parcel_id: str,
    project_id: str,
    old_stage: str,
    new_stage: str,
    changed_by: str = None,
):
    """Emit a workflow stage change notification."""
    notification = await create_notification(
        notification_type=NotificationType.WORKFLOW_CHANGE,
        title="Workflow Updated",
        message=f"Parcel moved from {old_stage} to {new_stage}",
        data={
            "parcel_id": parcel_id,
            "project_id": project_id,
            "old_stage": old_stage,
            "new_stage": new_stage,
            "changed_by": changed_by,
        },
        severity="success",
        action_url=f"/workbench?parcelId={parcel_id}",
    )
    
    await manager.broadcast_to_users(user_ids, notification)


async def emit_ai_escalation(
    user_ids: list[str],
    escalation_id: str,
    reason: str,
    priority: str,
    parcel_id: str = None,
    confidence: float = None,
):
    """Emit an AI escalation notification requiring human review."""
    severity_map = {"high": "error", "medium": "warning", "low": "info"}
    
    notification = await create_notification(
        notification_type=NotificationType.AI_ESCALATION,
        title="AI Review Required",
        message=reason,
        data={
            "escalation_id": escalation_id,
            "parcel_id": parcel_id,
            "priority": priority,
            "confidence": confidence,
        },
        severity=severity_map.get(priority, "warning"),
        action_url=f"/counsel?escalation={escalation_id}",
    )
    
    await manager.broadcast_to_users(user_ids, notification)


async def emit_offer_notification(
    user_ids: list[str],
    offer_id: str,
    parcel_id: str,
    offer_type: str,
    amount: float = None,
    is_response: bool = False,
):
    """Emit an offer or offer response notification."""
    notification = await create_notification(
        notification_type=NotificationType.OFFER_RESPONSE if is_response else NotificationType.OFFER_RECEIVED,
        title="Offer Response Received" if is_response else "New Offer Created",
        message=f"{'Counter offer' if is_response else 'Offer'} for ${amount:,.0f}" if amount else f"New {offer_type} offer",
        data={
            "offer_id": offer_id,
            "parcel_id": parcel_id,
            "offer_type": offer_type,
            "amount": amount,
        },
        severity="info",
        action_url=f"/workbench?parcelId={parcel_id}&tab=offers",
    )
    
    await manager.broadcast_to_users(user_ids, notification)


# =============================================================================
# WebSocket Endpoints
# =============================================================================

@router.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    """WebSocket endpoint for receiving real-time notifications.
    
    Connection protocol:
    1. Connect to /ws/notifications
    2. Send authentication message: {"type": "auth", "user_id": "xxx", "token": "xxx"}
    3. Receive notifications as JSON messages
    
    Message types received:
    - connected: Connection established
    - notification: A notification event
    - ping: Keep-alive (client should respond with pong)
    
    Message types to send:
    - auth: Authenticate the connection
    - subscribe: Subscribe to topics
    - unsubscribe: Unsubscribe from topics
    - pong: Response to ping
    - ack: Acknowledge a notification as read
    """
    user_id = "anonymous"  # Will be set by auth message
    
    try:
        # Accept connection (auth happens via message)
        await websocket.accept()
        
        # Wait for auth message
        auth_timeout = 30  # seconds
        try:
            auth_data = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=auth_timeout
            )
            
            if auth_data.get("type") != "auth":
                await websocket.send_json({"type": "error", "message": "Expected auth message"})
                await websocket.close(code=4001)
                return
            
            user_id = auth_data.get("user_id", "anonymous")
            # In production, validate the token here
            # token = auth_data.get("token")
            
            # Register the connection
            if user_id not in manager.active_connections:
                manager.active_connections[user_id] = set()
                manager.subscriptions[user_id] = {"all"}
            
            manager.active_connections[user_id].add(websocket)
            manager.connection_users[websocket] = user_id
            
            await websocket.send_json({
                "type": "connected",
                "user_id": user_id,
                "subscriptions": list(manager.subscriptions.get(user_id, [])),
                "timestamp": datetime.utcnow().isoformat(),
            })
            
        except asyncio.TimeoutError:
            await websocket.send_json({"type": "error", "message": "Auth timeout"})
            await websocket.close(code=4002)
            return
        
        # Main message loop
        while True:
            try:
                data = await websocket.receive_json()
                msg_type = data.get("type")
                
                if msg_type == "subscribe":
                    topics = data.get("topics", [])
                    await manager.subscribe(user_id, topics)
                    await websocket.send_json({
                        "type": "subscribed",
                        "topics": topics,
                    })
                
                elif msg_type == "unsubscribe":
                    topics = data.get("topics", [])
                    await manager.unsubscribe(user_id, topics)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "topics": topics,
                    })
                
                elif msg_type == "pong":
                    # Client responded to ping, connection is alive
                    pass
                
                elif msg_type == "ack":
                    # Client acknowledged a notification
                    notification_id = data.get("notification_id")
                    # In production, mark as read in database
                    await websocket.send_json({
                        "type": "acked",
                        "notification_id": notification_id,
                    })
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WebSocket message error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: user={user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)


@router.get("/ws/status")
async def websocket_status():
    """Get WebSocket server status."""
    return {
        "status": "running",
        "total_connections": manager.total_connections,
        "connected_users": manager.connected_users,
    }


# =============================================================================
# REST API for testing notifications
# =============================================================================

@router.post("/ws/test/broadcast")
async def test_broadcast(
    title: str = "Test Notification",
    message: str = "This is a test notification",
    severity: str = "info",
):
    """Test endpoint to broadcast a notification to all connected clients."""
    notification = await create_notification(
        notification_type=NotificationType.SYSTEM,
        title=title,
        message=message,
        severity=severity,
    )
    await manager.broadcast(notification)
    return {"status": "sent", "connections": manager.total_connections}


@router.post("/ws/test/send/{user_id}")
async def test_send_to_user(
    user_id: str,
    title: str = "Personal Notification",
    message: str = "This is a personal notification",
    severity: str = "info",
):
    """Test endpoint to send a notification to a specific user."""
    notification = await create_notification(
        notification_type=NotificationType.SYSTEM,
        title=title,
        message=message,
        severity=severity,
    )
    await manager.send_personal(user_id, notification)
    return {"status": "sent", "user_id": user_id}
