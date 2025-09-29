from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
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


class Task(Base):
    """Task model for database"""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Task status and priority as strings
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
    
    # User relationship
    user_id = Column(Integer, nullable=False, index=True)
    
    # Timestamps - Fixed to handle timezone properly
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), 
        onupdate=func.now(),
        nullable=True
    )
    due_date = Column(
        DateTime(timezone=True), 
        nullable=True
    )
    completed_at = Column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    def to_dict(self) -> dict:
        """Convert task to dictionary with proper datetime handling"""
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
        }
    
    def mark_completed(self):
        """Mark task as completed with current timestamp"""
        self.status = TaskStatus.COMPLETED.value
        self.completed_at = datetime.now(timezone.utc)
    
    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}')>"