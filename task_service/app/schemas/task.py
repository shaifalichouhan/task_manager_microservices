from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum

class TaskStatus(str, Enum):
    """Task status enumeration for API"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskPriority(str, Enum):
    """Task priority enumeration for API"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskBase(BaseModel):
    """Base task schema"""
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: Optional[str] = Field(None, max_length=2000, description="Task description")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="Task priority")
    due_date: Optional[datetime] = Field(None, description="Task due date")
    tags: Optional[List[str]] = Field(default_factory=list, description="Task tags")
    estimated_hours: Optional[int] = Field(None, ge=0, le=1000, description="Estimated hours")

    @validator('tags')
    def validate_tags(cls, v):
        """Validate and clean tags"""
        if v is None:
            return []
        # Remove empty strings and limit to 10 tags
        clean_tags = [tag.strip() for tag in v if tag and tag.strip()]
        return clean_tags[:10]

    @validator('due_date')
    def validate_due_date(cls, v):
        """Validate due date is in the future"""
        if v and v < datetime.now():
            # Allow past dates but could add warning
            pass
        return v

class TaskCreate(TaskBase):
    """Schema for creating a task"""
    pass

class TaskUpdate(BaseModel):
    """Schema for updating a task"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    estimated_hours: Optional[int] = Field(None, ge=0, le=1000)
    actual_hours: Optional[int] = Field(None, ge=0, le=1000)

    @validator('tags')
    def validate_tags(cls, v):
        """Validate and clean tags"""
        if v is None:
            return v
        # Remove empty strings and limit to 10 tags
        clean_tags = [tag.strip() for tag in v if tag and tag.strip()]
        return clean_tags[:10] if clean_tags else None

class TaskStatusUpdate(BaseModel):
    """Schema for updating only task status"""
    status: TaskStatus

class TaskResponse(TaskBase):
    """Schema for task responses"""
    id: int
    status: TaskStatus
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    actual_hours: Optional[int] = None

    class Config:
        from_attributes = True

class TaskListResponse(BaseModel):
    """Schema for paginated task list responses"""
    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class TaskSummary(BaseModel):
    """Schema for task summary statistics"""
    total_tasks: int
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    cancelled_tasks: int
    overdue_tasks: int

class TaskFilter(BaseModel):
    """Schema for task filtering"""
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    tags: Optional[List[str]] = None
    due_before: Optional[datetime] = None
    due_after: Optional[datetime] = None
    search: Optional[str] = Field(None, max_length=100, description="Search in title and description")
    
    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    
    # Sorting
    sort_by: Optional[str] = Field("created_at", description="Field to sort by")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$", description="Sort order")