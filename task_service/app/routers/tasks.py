from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

from ..core.rabbitmq import rabbitmq_publisher
from ..core.database import get_db
from ..core.auth import get_current_user, CurrentUser
from ..models.task import Task, TaskStatus, TaskPriority
from ..schemas.task import (
    TaskCreate, TaskUpdate, TaskResponse, TaskList,
    TaskStatus as SchemaTaskStatus, TaskPriority as SchemaTaskPriority
)

router = APIRouter()


def convert_datetime_to_utc(dt) -> datetime:
    """Convert datetime to UTC timezone-aware datetime"""
    if dt is None:
        return None
    
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            # Naive datetime, assume UTC
            return dt.replace(tzinfo=timezone.utc)
        else:
            # Already timezone-aware, convert to UTC
            return dt.astimezone(timezone.utc)
    
    return dt


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new task for the authenticated user"""
    try:
        # Convert due_date to UTC if provided
        due_date_utc = None
        if task_data.due_date:
            due_date_utc = convert_datetime_to_utc(task_data.due_date)
        
        # Create task instance
        db_task = Task(
            title=task_data.title,
            description=task_data.description,
            priority=task_data.priority.value if task_data.priority else TaskPriority.MEDIUM.value,
            due_date=due_date_utc,
            user_id=current_user.user_id
        )
        
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        
        return TaskResponse(
            id=db_task.id,
            title=db_task.title,
            description=db_task.description,
            status=SchemaTaskStatus(db_task.status),
            priority=SchemaTaskPriority(db_task.priority),
            user_id=db_task.user_id,
            created_at=db_task.created_at,
            updated_at=db_task.updated_at,
            due_date=db_task.due_date,
            completed_at=db_task.completed_at,
            tags=getattr(task_data, 'tags', [])
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating task: {str(e)}"
        )


@router.get("/", response_model=TaskList)
async def get_tasks(
    skip: int = Query(0, ge=0, description="Number of tasks to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of tasks to return"),
    status_filter: Optional[SchemaTaskStatus] = Query(None, description="Filter by status"),
    priority_filter: Optional[SchemaTaskPriority] = Query(None, description="Filter by priority"),
    search: Optional[str] = Query(None, min_length=1, max_length=100, description="Search in title and description"),
    sort_by: str = Query("created_at", pattern="^(created_at|updated_at|due_date|title|priority)$", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get tasks for the authenticated user with filtering and pagination"""
    
    # Base query - only user's tasks
    query = db.query(Task).filter(Task.user_id == current_user.user_id)
    
    # Apply filters
    if status_filter:
        query = query.filter(Task.status == status_filter.value)
    
    if priority_filter:
        query = query.filter(Task.priority == priority_filter.value)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Task.title.ilike(search_term),
                Task.description.ilike(search_term)
            )
        )
    
    # Apply sorting
    sort_column = getattr(Task, sort_by)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))
    
    # Get total count before pagination
    total = query.count()
    
    # Apply pagination
    tasks = query.offset(skip).limit(limit).all()
    
    # Convert to response models
    task_responses = []
    for task in tasks:
        task_responses.append(TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            status=SchemaTaskStatus(task.status),
            priority=SchemaTaskPriority(task.priority),
            user_id=task.user_id,
            created_at=task.created_at,
            updated_at=task.updated_at,
            due_date=task.due_date,
            completed_at=task.completed_at,
            tags=[]  # Add tags if you implement them
        ))
    
    return TaskList(
        tasks=task_responses,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific task by ID"""
    task = db.query(Task).filter(
        and_(Task.id == task_id, Task.user_id == current_user.user_id)
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=SchemaTaskStatus(task.status),
        priority=SchemaTaskPriority(task.priority),
        user_id=task.user_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
        due_date=task.due_date,
        completed_at=task.completed_at,
        tags=[]
    )


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a task"""
    task = db.query(Task).filter(
        and_(Task.id == task_id, Task.user_id == current_user.user_id)
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    try:
        # Update fields if provided
        update_data = task_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if field == "due_date" and value:
                value = convert_datetime_to_utc(value)
            elif field in ["status", "priority"] and hasattr(value, 'value'):
                value = value.value
            
            setattr(task, field, value)
        
        # Update timestamp
        task.updated_at = datetime.now(timezone.utc)
        
        # If status changed to completed, set completed_at
        if task_update.status == SchemaTaskStatus.COMPLETED and not task.completed_at:
            task.completed_at = datetime.now(timezone.utc)
        elif task_update.status and task_update.status != SchemaTaskStatus.COMPLETED:
            task.completed_at = None
        
        db.commit()
        db.refresh(task)
        
        return TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            status=SchemaTaskStatus(task.status),
            priority=SchemaTaskPriority(task.priority),
            user_id=task.user_id,
            created_at=task.created_at,
            updated_at=task.updated_at,
            due_date=task.due_date,
            completed_at=task.completed_at,
            tags=[]
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating task: {str(e)}"
        )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a task"""
    task = db.query(Task).filter(
        and_(Task.id == task_id, Task.user_id == current_user.user_id)
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    try:
        db.delete(task)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting task: {str(e)}"
        )
@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new task for the authenticated user"""
    try:
        # Convert due_date to UTC if provided
        due_date_utc = None
        if task_data.due_date:
            due_date_utc = convert_datetime_to_utc(task_data.due_date)
        
        # Create task instance
        db_task = Task(
            title=task_data.title,
            description=task_data.description,
            priority=task_data.priority.value if task_data.priority else TaskPriority.MEDIUM.value,
            due_date=due_date_utc,
            user_id=current_user.user_id
        )
        
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        
        # Publish event to RabbitMQ
        try:
            event_data = {
                'task_id': db_task.id,
                'title': db_task.title,
                'description': db_task.description,
                'priority': db_task.priority,
                'user_email': current_user.email,
                'user_id': current_user.user_id,
                'created_at': db_task.created_at.isoformat() if db_task.created_at else None
            }
            rabbitmq_publisher.publish_event('task_created', event_data)
        except Exception as e:
            logger.warning(f"Failed to publish task_created event: {e}")
            # Don't fail the task creation if event publishing fails
        
        return TaskResponse(
            id=db_task.id,
            title=db_task.title,
            description=db_task.description,
            status=SchemaTaskStatus(db_task.status),
            priority=SchemaTaskPriority(db_task.priority),
            user_id=db_task.user_id,
            created_at=db_task.created_at,
            updated_at=db_task.updated_at,
            due_date=db_task.due_date,
            completed_at=db_task.completed_at,
            tags=getattr(task_data, 'tags', [])
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating task: {str(e)}"
        )