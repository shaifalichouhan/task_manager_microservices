"""
Pydantic schemas for Task Service.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
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


class TaskBase(BaseModel):
    """Base task schema"""
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: Optional[str] = Field(None, max_length=1000, description="Task description")
    priority: Optional[TaskPriority] = Field(TaskPriority.MEDIUM, description="Task priority")
    due_date: Optional[datetime] = Field(None, description="Task due date")
    tags: Optional[List[str]] = Field(default_factory=list, description="Task tags")


class TaskCreate(TaskBase):
    """Schema for creating a task"""
    pass


class TaskUpdate(BaseModel):
    """Schema for updating a task"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Task title")
    description: Optional[str] = Field(None, max_length=1000, description="Task description")
    status: Optional[TaskStatus] = Field(None, description="Task status")
    priority: Optional[TaskPriority] = Field(None, description="Task priority")
    due_date: Optional[datetime] = Field(None, description="Task due date")
    tags: Optional[List[str]] = Field(None, description="Task tags")


class TaskResponse(TaskBase):
    """Schema for task response"""
    id: int = Field(..., description="Task ID")
    status: TaskStatus = Field(..., description="Task status")
    user_id: int = Field(..., description="User ID who owns the task")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Task update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Task completion timestamp")
    
    class Config:
        from_attributes = True


class TaskSummary(BaseModel):
    """Schema for task summary statistics"""
    total_tasks: int = Field(..., description="Total number of tasks")
    pending_tasks: int = Field(..., description="Number of pending tasks")
    in_progress_tasks: int = Field(..., description="Number of in-progress tasks")
    completed_tasks: int = Field(..., description="Number of completed tasks")
    cancelled_tasks: int = Field(..., description="Number of cancelled tasks")
    overdue_tasks: int = Field(..., description="Number of overdue tasks")


class TaskList(BaseModel):
    """Schema for paginated task list"""
    tasks: List[TaskResponse] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks")
    skip: int = Field(..., description="Number of tasks skipped")
    limit: int = Field(..., description="Number of tasks returned")
    has_next: bool = Field(default=False, description="Whether there are more tasks")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Calculate has_next based on total, skip, and limit
        self.has_next = (self.skip + self.limit) < self.total