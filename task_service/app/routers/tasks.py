from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

from ..core.database import get_db
from ..core.auth import get_current_active_user
from ..models.task import Task, TaskStatus as DBTaskStatus, TaskPriority as DBTaskPriority
from ..schemas.task import (
    TaskCreate, TaskUpdate, TaskResponse, TaskListResponse, 
    TaskStatusUpdate, TaskSummary, TaskStatus, TaskPriority
)

router = APIRouter()

def convert_enum_values(task: Task) -> dict:
    """Convert database enum values to schema format"""
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,  # Already a string
        "priority": task.priority,  # Already a string
        "user_id": task.user_id,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "due_date": task.due_date,
        "completed_at": task.completed_at,
        "tags": task.tags.split(",") if task.tags else [],
        "estimated_hours": task.estimated_hours,
        "actual_hours": task.actual_hours
    }

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: dict = Depends(get_current_active_user),  # Authentication required
    db: Session = Depends(get_db)
):
    """Create a new task - Authentication Required"""
    try:
        # Convert string tags to comma-separated string for database
        tags_str = ",".join(task_data.tags) if task_data.tags else None
        
        # Create task instance
        db_task = Task(
            title=task_data.title,
            description=task_data.description,
            priority=DBTaskPriority(task_data.priority.value),
            due_date=task_data.due_date,
            user_id=current_user["id"],  # Associate with authenticated user
            tags=tags_str,
            estimated_hours=task_data.estimated_hours,
            status=DBTaskStatus.PENDING
        )
        
        # Save to database
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        
        return TaskResponse(**convert_enum_values(db_task))
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
        )

@router.get("/", response_model=TaskListResponse)
async def get_tasks(
    status_filter: Optional[TaskStatus] = Query(None, alias="status", description="Filter by status"),
    priority_filter: Optional[TaskPriority] = Query(None, alias="priority", description="Filter by priority"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: dict = Depends(get_current_active_user),  # Authentication required
    db: Session = Depends(get_db)
):
    """Get paginated list of user's tasks - Authentication Required"""
    try:
        # Base query - only authenticated user's tasks
        query = db.query(Task).filter(Task.user_id == current_user["id"])
        
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
        if hasattr(Task, sort_by):
            sort_column = getattr(Task, sort_by)
            if sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(Task.created_at))
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        tasks = query.offset(offset).limit(page_size).all()
        
        # Convert tasks to response format
        task_responses = [TaskResponse(**convert_enum_values(task)) for task in tasks]
        
        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size
        
        return TaskListResponse(
            tasks=task_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch tasks: {str(e)}"
        )

@router.get("/summary", response_model=TaskSummary)
async def get_task_summary(
    current_user: dict = Depends(get_current_active_user),  # Authentication required
    db: Session = Depends(get_db)
):
    """Get task summary statistics - Authentication Required"""
    try:
        user_id = current_user["id"]
        
        # Count tasks by status for authenticated user only
        total_tasks = db.query(Task).filter(Task.user_id == user_id).count()
        pending_tasks = db.query(Task).filter(
            and_(Task.user_id == user_id, Task.status == DBTaskStatus.PENDING.value)
        ).count()
        in_progress_tasks = db.query(Task).filter(
            and_(Task.user_id == user_id, Task.status == DBTaskStatus.IN_PROGRESS.value)
        ).count()
        completed_tasks = db.query(Task).filter(
            and_(Task.user_id == user_id, Task.status == DBTaskStatus.COMPLETED.value)
        ).count()
        cancelled_tasks = db.query(Task).filter(
            and_(Task.user_id == user_id, Task.status == DBTaskStatus.CANCELLED.value)
        ).count()
        
        # Count overdue tasks
        now = datetime.now()
        overdue_tasks = db.query(Task).filter(
            and_(
                Task.user_id == user_id,
                Task.due_date < now,
                Task.status.notin_([DBTaskStatus.COMPLETED.value, DBTaskStatus.CANCELLED.value])
            )
        ).count()
        
        return TaskSummary(
            total_tasks=total_tasks,
            pending_tasks=pending_tasks,
            in_progress_tasks=in_progress_tasks,
            completed_tasks=completed_tasks,
            cancelled_tasks=cancelled_tasks,
            overdue_tasks=overdue_tasks
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch task summary: {str(e)}"
        )

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: dict = Depends(get_current_active_user),  # Authentication required
    db: Session = Depends(get_db)
):
    """Get a specific task by ID - Authentication Required"""
    task = db.query(Task).filter(
        and_(Task.id == task_id, Task.user_id == current_user["id"])  # User isolation
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )
    
    return TaskResponse(**convert_enum_values(task))

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    current_user: dict = Depends(get_current_active_user),  # Authentication required
    db: Session = Depends(get_db)
):
    """Update a task - Authentication Required"""
    # Get task (user isolation)
    task = db.query(Task).filter(
        and_(Task.id == task_id, Task.user_id == current_user["id"])
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )
    
    try:
        # Update fields
        update_data = task_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if field == "status" and value:
                new_status = DBTaskStatus(value.value)
                if new_status == DBTaskStatus.COMPLETED and task.status != DBTaskStatus.COMPLETED:
                    task.completed_at = datetime.now()
                elif new_status != DBTaskStatus.COMPLETED:
                    task.completed_at = None
                task.status = new_status
            elif field == "priority" and value:
                task.priority = DBTaskPriority(value.value)
            elif field == "tags" and value is not None:
                task.tags = ",".join(value) if value else None
            elif hasattr(task, field):
                setattr(task, field, value)
        
        task.updated_at = datetime.now()
        
        db.commit()
        db.refresh(task)
        
        return TaskResponse(**convert_enum_values(task))
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task: {str(e)}"
        )

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: dict = Depends(get_current_active_user),  # Authentication required
    db: Session = Depends(get_db)
):
    """Delete a task - Authentication Required"""
    # Get task (user isolation)
    task = db.query(Task).filter(
        and_(Task.id == task_id, Task.user_id == current_user["id"])
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )
    
    try:
        db.delete(task)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete task: {str(e)}"
        )