import json
import logging
from typing import Dict, Any
import pika
import pika.exceptions
import time

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    """RabbitMQ publisher for task events"""
    
    def __init__(self, host: str = "rabbitmq", port: int = 5672, user: str = "admin", password: str = "admin123"):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.connection = None
        self.channel = None
        self.exchange = "task_exchange"
        self.routing_key = "task.created"
    
    def connect(self) -> bool:
        """Establish connection to RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(self.user, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300,
            )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare exchange
            self.channel.exchange_declare(
                exchange=self.exchange,
                exchange_type='topic',
                durable=True
            )
            
            logger.info(f"Connected to RabbitMQ at {self.host}:{self.port}")
            return True
            
        except pika.exceptions.AMQPConnectionError as e:
            logger.warning(f"Could not connect to RabbitMQ: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to RabbitMQ: {e}")
            return False
    
    def publish_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Publish event to RabbitMQ"""
        if not self.connection or self.connection.is_closed:
            if not self.connect():
                logger.warning("Failed to publish event - no connection")
                return False
        
        try:
            message = {
                'event_type': event_type,
                'data': data
            }
            
            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=self.routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    content_type='application/json'
                )
            )
            
            logger.info(f"Published {event_type} event to RabbitMQ")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing event: {e}")
            return False
    
    def close(self):
        """Close connection"""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
    
    def connect(self, max_retries: int = 5, retry_delay: int = 5) -> bool:
        """Establish connection to RabbitMQ with retries"""
        for attempt in range(max_retries):
            try:
                credentials = pika.PlainCredentials(self.user, self.password)
                parameters = pika.ConnectionParameters(
                    host=self.host,
                    port=self.port,
                    credentials=credentials,
                    heartbeat=600,
                    blocked_connection_timeout=300,
                )
                
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                
                # Declare exchange
                self.channel.exchange_declare(
                    exchange=self.exchange,
                    exchange_type='topic',
                    durable=True
                )
                
                logger.info(f"Connected to RabbitMQ at {self.host}:{self.port}")
                return True
                
            except pika.exceptions.AMQPConnectionError as e:
                logger.warning(f"RabbitMQ connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to RabbitMQ after all retries")
                    return False
            except Exception as e:
                logger.error(f"Unexpected error connecting to RabbitMQ: {e}")
                return False
        
        return False


# Global publisher instance
rabbitmq_publisher = RabbitMQPublisher()