"""
Notification handlers for different event types.
"""
import json
import logging
import smtplib
import os
from datetime import datetime
from typing import Dict, Any, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class NotificationManager:
    """Manages different types of notifications"""
    
    def __init__(self):
        self.processed_notifications: List[Dict[str, Any]] = []
        self.ensure_log_directory()
    
    def ensure_log_directory(self):
        """Create log directory if it doesn't exist"""
        log_dir = os.path.dirname(settings.log_file_path)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
                logger.info(f"Created log directory: {log_dir}")
            except Exception as e:
                logger.error(f"Error creating log directory: {e}")
    
    def handle_task_created(self, message: Dict[str, Any]):
        """Handle task_created events"""
        try:
            event_data = message.get('data', {})
            task_info = {
                'task_id': event_data.get('task_id'),
                'title': event_data.get('title'),
                'user_email': event_data.get('user_email', 'unknown@example.com'),
                'created_at': event_data.get('created_at'),
                'priority': event_data.get('priority', 'medium')
            }
            
            logger.info(f"Processing task_created event for task: {task_info['title']}")
            
            # Send notifications
            if settings.enable_log_notifications:
                self.send_log_notification('task_created', task_info)
            
            if settings.enable_email_notifications:
                self.send_email_notification('task_created', task_info)
            
            # Store processed notification
            self.store_processed_notification('task_created', task_info, message)
            
        except Exception as e:
            logger.error(f"Error handling task_created event: {e}")
    
    def send_log_notification(self, event_type: str, data: Dict[str, Any]):
        """Send log-based notification"""
        try:
            timestamp = datetime.now().isoformat()
            log_entry = {
                'timestamp': timestamp,
                'event_type': event_type,
                'data': data
            }
            
            # Log to application log
            logger.info(f"NOTIFICATION: {event_type} - {data.get('title', 'Unknown')}")
            
            # Write to notification log file
            with open(settings.log_file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            logger.debug(f"Log notification sent for {event_type}")
            
        except Exception as e:
            logger.error(f"Error sending log notification: {e}")
    
    def send_email_notification(self, event_type: str, data: Dict[str, Any]):
        """Send email notification (simulated)"""
        if not settings.smtp_user or not settings.smtp_password:
            logger.info(f"Email notification simulated for {event_type} (no SMTP config)")
            return
        
        try:
            # Create email content
            if event_type == 'task_created':
                subject = f"New Task Created: {data.get('title', 'Unknown')}"
                body = self.create_task_created_email_body(data)
            else:
                subject = f"Task Manager Notification: {event_type}"
                body = f"Event: {event_type}\nData: {json.dumps(data, indent=2)}"
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = settings.from_email
            msg['To'] = data.get('user_email', 'user@example.com')
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email (in production environment)
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                text = msg.as_string()
                server.sendmail(settings.from_email, [data.get('user_email')], text)
            
            logger.info(f"Email notification sent for {event_type}")
            
        except Exception as e:
            # Log the attempt but don't fail the notification process
            logger.info(f"Email notification simulated for {event_type} (error: {e})")
    
    def create_task_created_email_body(self, data: Dict[str, Any]) -> str:
        """Create email body for task created notification"""
        return f"""
Dear User,

A new task has been created in your Task Manager:

Task Details:
- Title: {data.get('title', 'Unknown')}
- Priority: {data.get('priority', 'Medium')}
- Created: {data.get('created_at', 'Unknown')}

You can view and manage your tasks at: http://localhost:8000/api/v1/tasks/

Best regards,
Task Manager Notification System
        """.strip()
    
    def store_processed_notification(self, event_type: str, data: Dict[str, Any], original_message: Dict[str, Any]):
        """Store processed notification for /logs endpoint"""
        notification_record = {
            'id': len(self.processed_notifications) + 1,
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'status': 'processed',
            'data': data,
            'original_message': original_message,
            'notifications_sent': {
                'log': settings.enable_log_notifications,
                'email': settings.enable_email_notifications
            }
        }
        
        # Keep only last 100 notifications in memory
        if len(self.processed_notifications) >= 100:
            self.processed_notifications.pop(0)
        
        self.processed_notifications.append(notification_record)
        logger.debug(f"Stored notification record: {notification_record['id']}")
    
    def get_processed_notifications(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of processed notifications"""
        return self.processed_notifications[-limit:] if limit else self.processed_notifications
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        total_notifications = len(self.processed_notifications)
        event_types = {}
        
        for notification in self.processed_notifications:
            event_type = notification['event_type']
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        return {
            'total_processed': total_notifications,
            'event_types': event_types,
            'log_notifications_enabled': settings.enable_log_notifications,
            'email_notifications_enabled': settings.enable_email_notifications,
            'log_file': settings.log_file_path
        }


# Global notification manager
notification_manager = NotificationManager()