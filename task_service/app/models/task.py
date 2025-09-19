from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.sql import func
import enum

from ..core.database import Base

class TaskStatus(str, enum.Enum):
    """Task status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskPriority(str, enum.Enum):
    """Task priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class Task(Base):
    """Task model for database"""
    
    __tablename__ = "tasks"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Task details
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Task status and priority
    status = Column(
        String(20), 
        default=TaskStatus.PENDING.value,
        nullable=False,
        index=True
    )
    priority = Column(
        String(20),
        default=TaskPriority.MEDIUM.value,
        nullable=False,
        index=True
    )
    
    # User association (foreign key to user in auth service)
    user_id = Column(Integer, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional metadata
    tags = Column(String(500), nullable=True)  # Comma-separated tags
    estimated_hours = Column(Integer, nullable=True)  # Estimated time in hours
    actual_hours = Column(Integer, nullable=True)  # Actual time spent in hours
    
    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status.value}', user_id={self.user_id})>"
    
    def to_dict(self) -> dict:
        """Convert task to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tags": self.tags.split(",") if self.tags else [],
            "estimated_hours": self.estimated_hours,
            "actual_hours": self.actual_hours
        }