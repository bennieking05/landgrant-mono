"""Task Management API.

Provides comprehensive task management with auto-assignment,
priority management, and workload balancing.
"""

from datetime import datetime, timedelta
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from pydantic import BaseModel, Field
from uuid import uuid4
from enum import Enum

from app.api.deps import get_db, get_current_persona
from app.db import models
from app.db.models import Persona, Task
from app.security.rbac import authorize, Action

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# =============================================================================
# Enums and Constants
# =============================================================================

class TaskStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskCategory(str, Enum):
    DOCUMENT_REVIEW = "document_review"
    APPROVAL_REQUIRED = "approval_required"
    OWNER_CONTACT = "owner_contact"
    DEADLINE_ACTION = "deadline_action"
    OFFER_PREPARATION = "offer_preparation"
    APPRAISAL_REVIEW = "appraisal_review"
    LITIGATION_PREP = "litigation_prep"
    GENERAL = "general"


# Default task priorities by category
CATEGORY_PRIORITIES = {
    TaskCategory.DEADLINE_ACTION: TaskPriority.CRITICAL,
    TaskCategory.APPROVAL_REQUIRED: TaskPriority.HIGH,
    TaskCategory.LITIGATION_PREP: TaskPriority.HIGH,
    TaskCategory.DOCUMENT_REVIEW: TaskPriority.MEDIUM,
    TaskCategory.OFFER_PREPARATION: TaskPriority.MEDIUM,
    TaskCategory.APPRAISAL_REVIEW: TaskPriority.MEDIUM,
    TaskCategory.OWNER_CONTACT: TaskPriority.MEDIUM,
    TaskCategory.GENERAL: TaskPriority.LOW,
}

# Persona-based task routing
CATEGORY_PERSONA_ROUTING = {
    TaskCategory.DOCUMENT_REVIEW: [Persona.IN_HOUSE_COUNSEL, Persona.OUTSIDE_COUNSEL],
    TaskCategory.APPROVAL_REQUIRED: [Persona.IN_HOUSE_COUNSEL, Persona.OUTSIDE_COUNSEL],
    TaskCategory.OWNER_CONTACT: [Persona.LAND_AGENT],
    TaskCategory.DEADLINE_ACTION: [Persona.IN_HOUSE_COUNSEL, Persona.LAND_AGENT],
    TaskCategory.OFFER_PREPARATION: [Persona.LAND_AGENT],
    TaskCategory.APPRAISAL_REVIEW: [Persona.IN_HOUSE_COUNSEL],
    TaskCategory.LITIGATION_PREP: [Persona.IN_HOUSE_COUNSEL, Persona.OUTSIDE_COUNSEL],
    TaskCategory.GENERAL: [Persona.LAND_AGENT],
}


# =============================================================================
# Request/Response Models
# =============================================================================

class TaskCreateRequest(BaseModel):
    """Request to create a new task."""
    project_id: str = Field(..., description="Project ID")
    parcel_id: Optional[str] = Field(None, description="Optional parcel ID")
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    category: TaskCategory = Field(default=TaskCategory.GENERAL)
    priority: Optional[TaskPriority] = Field(None, description="Auto-set if not provided")
    persona: Optional[Persona] = Field(None, description="Target persona (auto-assigned if not set)")
    assigned_to: Optional[str] = Field(None, description="User ID to assign to")
    due_at: Optional[datetime] = Field(None)
    auto_assign: bool = Field(default=True, description="Automatically assign based on workload")


class TaskUpdateRequest(BaseModel):
    """Request to update a task."""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    category: Optional[TaskCategory] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    assigned_to: Optional[str] = None
    due_at: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=1000)


class TaskResponse(BaseModel):
    """Task response model."""
    id: str
    project_id: str
    parcel_id: Optional[str]
    title: str
    description: Optional[str]
    category: str
    priority: str
    status: str
    persona: str
    assigned_to: Optional[str]
    assigned_to_name: Optional[str]
    due_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    is_overdue: bool
    metadata: dict


class TaskListResponse(BaseModel):
    """Response for task list."""
    tasks: list[TaskResponse]
    total: int
    page: int
    page_size: int


class TaskStatsResponse(BaseModel):
    """Task statistics response."""
    total: int
    open: int
    in_progress: int
    completed: int
    overdue: int
    by_priority: dict[str, int]
    by_category: dict[str, int]
    by_assignee: list[dict[str, Any]]


class AssignmentSuggestion(BaseModel):
    """Auto-assignment suggestion."""
    user_id: str
    user_name: str
    persona: str
    current_workload: int
    reason: str
    score: float


# =============================================================================
# Helper Functions
# =============================================================================

def get_task_priority(category: TaskCategory, priority: Optional[TaskPriority]) -> TaskPriority:
    """Get task priority, defaulting based on category."""
    if priority:
        return priority
    return CATEGORY_PRIORITIES.get(category, TaskPriority.MEDIUM)


def get_task_persona(category: TaskCategory, persona: Optional[Persona]) -> Persona:
    """Get task persona, defaulting based on category."""
    if persona:
        return persona
    personas = CATEGORY_PERSONA_ROUTING.get(category, [Persona.LAND_AGENT])
    return personas[0] if personas else Persona.LAND_AGENT


def calculate_workload_score(user: models.User, db: Session) -> int:
    """Calculate current workload score for a user."""
    now = datetime.utcnow()
    
    # Count open and in-progress tasks
    open_tasks = db.query(func.count(Task.id)).filter(
        Task.assigned_to == user.id,
        Task.status.in_(["open", "in_progress"]),
    ).scalar() or 0
    
    # Count overdue tasks (weighted higher)
    overdue_tasks = db.query(func.count(Task.id)).filter(
        Task.assigned_to == user.id,
        Task.status.in_(["open", "in_progress"]),
        Task.due_at < now,
    ).scalar() or 0
    
    # Count high priority tasks
    high_priority = db.query(func.count(Task.id)).filter(
        Task.assigned_to == user.id,
        Task.status.in_(["open", "in_progress"]),
        Task.metadata_json["priority"].astext.in_(["critical", "high"]),
    ).scalar() or 0
    
    # Calculate weighted score
    return open_tasks + (overdue_tasks * 3) + (high_priority * 2)


def find_best_assignee(
    db: Session,
    persona: Persona,
    project_id: Optional[str] = None,
) -> Optional[models.User]:
    """Find the best user to assign a task to based on workload."""
    # Get all users with the required persona
    users = db.query(models.User).filter(
        models.User.persona == persona,
    ).all()
    
    if not users:
        return None
    
    # Calculate workload scores
    scored_users = []
    for user in users:
        score = calculate_workload_score(user, db)
        scored_users.append((user, score))
    
    # Sort by score (lowest = best)
    scored_users.sort(key=lambda x: x[1])
    
    return scored_users[0][0] if scored_users else None


def task_to_response(task: Task, db: Session) -> TaskResponse:
    """Convert Task model to response."""
    assignee_name = None
    if task.assigned_to:
        assignee = db.query(models.User).filter(models.User.id == task.assigned_to).first()
        if assignee:
            assignee_name = assignee.full_name
    
    metadata = task.metadata_json or {}
    is_overdue = False
    if task.due_at and task.status in ["open", "in_progress"]:
        is_overdue = task.due_at < datetime.utcnow()
    
    return TaskResponse(
        id=task.id,
        project_id=task.project_id,
        parcel_id=task.parcel_id,
        title=task.title,
        description=metadata.get("description"),
        category=metadata.get("category", "general"),
        priority=metadata.get("priority", "medium"),
        status=task.status or "open",
        persona=task.persona.value if hasattr(task.persona, 'value') else str(task.persona),
        assigned_to=task.assigned_to,
        assigned_to_name=assignee_name,
        due_at=task.due_at,
        created_at=metadata.get("created_at", datetime.utcnow()),
        updated_at=metadata.get("updated_at"),
        is_overdue=is_overdue,
        metadata=metadata,
    )


# =============================================================================
# CRUD Endpoints
# =============================================================================

@router.post("", response_model=TaskResponse)
def create_task(
    request: TaskCreateRequest,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Create a new task with optional auto-assignment."""
    authorize(persona, "task", Action.CREATE)
    
    # Verify project exists
    project = db.query(models.Project).filter(models.Project.id == request.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {request.project_id}")
    
    # Verify parcel if provided
    if request.parcel_id:
        parcel = db.query(models.Parcel).filter(models.Parcel.id == request.parcel_id).first()
        if not parcel:
            raise HTTPException(status_code=404, detail=f"Parcel not found: {request.parcel_id}")
    
    # Determine priority and persona
    priority = get_task_priority(request.category, request.priority)
    task_persona = get_task_persona(request.category, request.persona)
    
    # Auto-assign if requested and no assignee specified
    assigned_to = request.assigned_to
    if request.auto_assign and not assigned_to:
        best_assignee = find_best_assignee(db, task_persona, request.project_id)
        if best_assignee:
            assigned_to = best_assignee.id
    
    # Create task
    now = datetime.utcnow()
    task = Task(
        id=str(uuid4()),
        project_id=request.project_id,
        parcel_id=request.parcel_id,
        title=request.title,
        persona=task_persona,
        assigned_to=assigned_to,
        due_at=request.due_at,
        status="open",
        metadata_json={
            "description": request.description,
            "category": request.category.value,
            "priority": priority.value,
            "created_at": now.isoformat(),
            "created_by": str(persona.value),
            "auto_assigned": request.auto_assign and assigned_to is not None,
        },
    )
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    return task_to_response(task, db)


@router.get("", response_model=TaskListResponse)
def list_tasks(
    project_id: Optional[str] = Query(None),
    parcel_id: Optional[str] = Query(None),
    status: Optional[TaskStatus] = Query(None),
    priority: Optional[TaskPriority] = Query(None),
    category: Optional[TaskCategory] = Query(None),
    assigned_to: Optional[str] = Query(None),
    my_tasks: bool = Query(False, description="Show only my assigned tasks"),
    overdue_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """List tasks with filtering and pagination."""
    authorize(persona, "task", Action.READ)
    
    query = db.query(Task)
    
    # Apply filters
    if project_id:
        query = query.filter(Task.project_id == project_id)
    if parcel_id:
        query = query.filter(Task.parcel_id == parcel_id)
    if status:
        query = query.filter(Task.status == status.value)
    if priority:
        query = query.filter(Task.metadata_json["priority"].astext == priority.value)
    if category:
        query = query.filter(Task.metadata_json["category"].astext == category.value)
    if assigned_to:
        query = query.filter(Task.assigned_to == assigned_to)
    if overdue_only:
        query = query.filter(
            Task.due_at < datetime.utcnow(),
            Task.status.in_(["open", "in_progress"]),
        )
    
    # Get total count
    total = query.count()
    
    # Order by priority (critical first), then due date
    priority_order = func.case(
        (Task.metadata_json["priority"].astext == "critical", 1),
        (Task.metadata_json["priority"].astext == "high", 2),
        (Task.metadata_json["priority"].astext == "medium", 3),
        else_=4,
    )
    query = query.order_by(priority_order, Task.due_at.asc().nullslast())
    
    # Paginate
    offset = (page - 1) * page_size
    tasks = query.offset(offset).limit(page_size).all()
    
    return TaskListResponse(
        tasks=[task_to_response(t, db) for t in tasks],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/my", response_model=TaskListResponse)
def get_my_tasks(
    status: Optional[TaskStatus] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get tasks assigned to the current user."""
    authorize(persona, "task", Action.READ)
    
    # Get user by persona (simplified - in production would use actual user ID)
    user = db.query(models.User).filter(models.User.persona == persona).first()
    if not user:
        return TaskListResponse(tasks=[], total=0, page=page, page_size=page_size)
    
    query = db.query(Task).filter(Task.assigned_to == user.id)
    
    if status:
        query = query.filter(Task.status == status.value)
    
    total = query.count()
    
    priority_order = func.case(
        (Task.metadata_json["priority"].astext == "critical", 1),
        (Task.metadata_json["priority"].astext == "high", 2),
        (Task.metadata_json["priority"].astext == "medium", 3),
        else_=4,
    )
    query = query.order_by(priority_order, Task.due_at.asc().nullslast())
    
    offset = (page - 1) * page_size
    tasks = query.offset(offset).limit(page_size).all()
    
    return TaskListResponse(
        tasks=[task_to_response(t, db) for t in tasks],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get a specific task by ID."""
    authorize(persona, "task", Action.READ)
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    
    return task_to_response(task, db)


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str,
    request: TaskUpdateRequest,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Update a task."""
    authorize(persona, "task", Action.UPDATE)
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    
    # Update fields
    if request.title:
        task.title = request.title
    if request.status:
        task.status = request.status.value
    if request.assigned_to is not None:
        task.assigned_to = request.assigned_to if request.assigned_to else None
    if request.due_at is not None:
        task.due_at = request.due_at
    
    # Update metadata
    metadata = task.metadata_json or {}
    if request.description is not None:
        metadata["description"] = request.description
    if request.category:
        metadata["category"] = request.category.value
    if request.priority:
        metadata["priority"] = request.priority.value
    if request.notes:
        if "notes" not in metadata:
            metadata["notes"] = []
        metadata["notes"].append({
            "text": request.notes,
            "by": str(persona.value),
            "at": datetime.utcnow().isoformat(),
        })
    
    metadata["updated_at"] = datetime.utcnow().isoformat()
    metadata["updated_by"] = str(persona.value)
    task.metadata_json = metadata
    
    db.commit()
    db.refresh(task)
    
    return task_to_response(task, db)


@router.post("/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: str,
    notes: Optional[str] = None,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Mark a task as completed."""
    authorize(persona, "task", Action.UPDATE)
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    
    task.status = "completed"
    
    metadata = task.metadata_json or {}
    metadata["completed_at"] = datetime.utcnow().isoformat()
    metadata["completed_by"] = str(persona.value)
    if notes:
        metadata["completion_notes"] = notes
    task.metadata_json = metadata
    
    db.commit()
    db.refresh(task)
    
    return task_to_response(task, db)


@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Delete (cancel) a task."""
    authorize(persona, "task", Action.DELETE)
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    
    # Soft delete by setting status to cancelled
    task.status = "cancelled"
    metadata = task.metadata_json or {}
    metadata["cancelled_at"] = datetime.utcnow().isoformat()
    metadata["cancelled_by"] = str(persona.value)
    task.metadata_json = metadata
    
    db.commit()
    
    return {"message": f"Task {task_id} cancelled"}


# =============================================================================
# Assignment Endpoints
# =============================================================================

@router.post("/{task_id}/assign")
def assign_task(
    task_id: str,
    user_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Assign a task to a specific user."""
    authorize(persona, "task", Action.UPDATE)
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found: {user_id}")
    
    task.assigned_to = user_id
    
    metadata = task.metadata_json or {}
    metadata["assigned_at"] = datetime.utcnow().isoformat()
    metadata["assigned_by"] = str(persona.value)
    task.metadata_json = metadata
    
    db.commit()
    
    return {"message": f"Task assigned to {user.full_name or user_id}"}


@router.get("/{task_id}/suggest-assignee", response_model=list[AssignmentSuggestion])
def suggest_assignee(
    task_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get assignment suggestions for a task based on workload."""
    authorize(persona, "task", Action.READ)
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    
    # Get users with matching persona
    users = db.query(models.User).filter(
        models.User.persona == task.persona,
    ).all()
    
    suggestions = []
    for user in users:
        workload = calculate_workload_score(user, db)
        score = 100 - min(workload * 5, 90)  # Higher score = better assignment
        
        reason = "Available capacity"
        if workload == 0:
            reason = "No current tasks - available immediately"
        elif workload < 5:
            reason = "Light workload - good availability"
        elif workload < 10:
            reason = "Moderate workload"
        else:
            reason = "Heavy workload - consider others first"
        
        suggestions.append(AssignmentSuggestion(
            user_id=user.id,
            user_name=user.full_name or user.email,
            persona=user.persona.value if hasattr(user.persona, 'value') else str(user.persona),
            current_workload=workload,
            reason=reason,
            score=score,
        ))
    
    # Sort by score (highest first)
    suggestions.sort(key=lambda x: x.score, reverse=True)
    
    return suggestions


@router.post("/{task_id}/auto-assign", response_model=TaskResponse)
def auto_assign_task(
    task_id: str,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Automatically assign a task based on workload balancing."""
    authorize(persona, "task", Action.UPDATE)
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    
    best_assignee = find_best_assignee(db, task.persona, task.project_id)
    if not best_assignee:
        raise HTTPException(
            status_code=400,
            detail=f"No available users with persona {task.persona}"
        )
    
    task.assigned_to = best_assignee.id
    
    metadata = task.metadata_json or {}
    metadata["auto_assigned"] = True
    metadata["assigned_at"] = datetime.utcnow().isoformat()
    metadata["assigned_by"] = "auto_assignment"
    task.metadata_json = metadata
    
    db.commit()
    db.refresh(task)
    
    return task_to_response(task, db)


# =============================================================================
# Statistics Endpoints
# =============================================================================

@router.get("/stats/summary", response_model=TaskStatsResponse)
def get_task_stats(
    project_id: Optional[str] = Query(None),
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Get task statistics summary."""
    authorize(persona, "task", Action.READ)
    
    query = db.query(Task)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    
    now = datetime.utcnow()
    
    # Basic counts
    total = query.count()
    open_count = query.filter(Task.status == "open").count()
    in_progress = query.filter(Task.status == "in_progress").count()
    completed = query.filter(Task.status == "completed").count()
    overdue = query.filter(
        Task.due_at < now,
        Task.status.in_(["open", "in_progress"]),
    ).count()
    
    # By priority
    by_priority = {}
    for priority in TaskPriority:
        count = query.filter(
            Task.metadata_json["priority"].astext == priority.value,
        ).count()
        by_priority[priority.value] = count
    
    # By category
    by_category = {}
    for category in TaskCategory:
        count = query.filter(
            Task.metadata_json["category"].astext == category.value,
        ).count()
        by_category[category.value] = count
    
    # By assignee
    assignee_stats = db.query(
        Task.assigned_to,
        func.count(Task.id).label("count"),
    ).filter(
        Task.assigned_to.isnot(None),
        Task.status.in_(["open", "in_progress"]),
    ).group_by(Task.assigned_to).all()
    
    by_assignee = []
    for user_id, count in assignee_stats:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        by_assignee.append({
            "user_id": user_id,
            "user_name": user.full_name if user else user_id,
            "count": count,
        })
    
    return TaskStatsResponse(
        total=total,
        open=open_count,
        in_progress=in_progress,
        completed=completed,
        overdue=overdue,
        by_priority=by_priority,
        by_category=by_category,
        by_assignee=by_assignee,
    )


# =============================================================================
# Bulk Operations
# =============================================================================

class BulkAssignRequest(BaseModel):
    """Request for bulk task assignment."""
    task_ids: list[str]
    user_id: str


class BulkStatusRequest(BaseModel):
    """Request for bulk status update."""
    task_ids: list[str]
    status: TaskStatus


@router.post("/bulk/assign")
def bulk_assign_tasks(
    request: BulkAssignRequest,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Assign multiple tasks to a user."""
    authorize(persona, "task", Action.UPDATE)
    
    user = db.query(models.User).filter(models.User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found: {request.user_id}")
    
    updated = 0
    for task_id in request.task_ids:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.assigned_to = request.user_id
            metadata = task.metadata_json or {}
            metadata["bulk_assigned_at"] = datetime.utcnow().isoformat()
            task.metadata_json = metadata
            updated += 1
    
    db.commit()
    
    return {"message": f"Assigned {updated} tasks to {user.full_name or user.id}"}


@router.post("/bulk/status")
def bulk_update_status(
    request: BulkStatusRequest,
    persona: Persona = Depends(get_current_persona),
    db: Session = Depends(get_db),
):
    """Update status for multiple tasks."""
    authorize(persona, "task", Action.UPDATE)
    
    updated = 0
    for task_id in request.task_ids:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = request.status.value
            metadata = task.metadata_json or {}
            metadata["status_updated_at"] = datetime.utcnow().isoformat()
            task.metadata_json = metadata
            updated += 1
    
    db.commit()
    
    return {"message": f"Updated status for {updated} tasks to {request.status.value}"}


# =============================================================================
# Health Check
# =============================================================================

@router.get("/health")
def tasks_health():
    """Health check for tasks service."""
    return {
        "status": "healthy",
        "service": "tasks",
        "timestamp": datetime.utcnow().isoformat(),
    }
