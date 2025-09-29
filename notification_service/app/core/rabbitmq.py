"""
RabbitMQ client for consuming task events.
"""
import json
import logging
import asyncio
from typing import Dict, Any, Callable
import pika
import pika.exceptions
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RabbitMQConsumer:
    """RabbitMQ consumer for task events"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.consuming = False
        self.message_handlers = {}
    
    def connect(self) -> bool:
        """Establish connection to RabbitMQ"""
        try:
            # Connection parameters
            credentials = pika.PlainCredentials(
                settings.rabbitmq_user,
                settings.rabbitmq_password
            )
            
            parameters = pika.ConnectionParameters(
                host=settings.rabbitmq_host,
                port=settings.rabbitmq_port,
                virtual_host=settings.rabbitmq_vhost,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300,
            )
            
            # Establish connection
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare exchange and queue
            self.setup_queue()
            
            logger.info(f"Connected to RabbitMQ at {settings.rabbitmq_host}:{settings.rabbitmq_port}")
            return True
            
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"RabbitMQ connection error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to RabbitMQ: {e}")
            return False
    
    def setup_queue(self):
        """Setup exchange, queue, and bindings"""
        try:
            # Declare exchange
            self.channel.exchange_declare(
                exchange=settings.rabbitmq_exchange,
                exchange_type='topic',
                durable=True
            )
            
            # Declare queue
            self.channel.queue_declare(
                queue=settings.rabbitmq_queue,
                durable=True
            )
            
            # Bind queue to exchange
            self.channel.queue_bind(
                exchange=settings.rabbitmq_exchange,
                queue=settings.rabbitmq_queue,
                routing_key=settings.rabbitmq_routing_key
            )
            
            logger.info(f"Queue setup completed: {settings.rabbitmq_queue}")
            
        except Exception as e:
            logger.error(f"Error setting up queue: {e}")
            raise
    
    def add_message_handler(self, event_type: str, handler: Callable):
        """Add message handler for specific event type"""
        self.message_handlers[event_type] = handler
        logger.info(f"Added handler for event type: {event_type}")
    
    def process_message(self, channel, method, properties, body):
        """Process incoming message from RabbitMQ"""
        try:
            # Parse message
            message = json.loads(body.decode('utf-8'))
            event_type = message.get('event_type', 'unknown')
            
            logger.info(f"Received message: {event_type}")
            logger.debug(f"Message content: {message}")
            
            # Find and execute handler
            handler = self.message_handlers.get(event_type)
            if handler:
                handler(message)
                logger.info(f"Successfully processed {event_type} event")
            else:
                logger.warning(f"No handler found for event type: {event_type}")
            
            # Acknowledge message
            channel.basic_ack(delivery_tag=method.delivery_tag)
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing message JSON: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def start_consuming(self):
        """Start consuming messages"""
        if not self.connection or self.connection.is_closed:
            if not self.connect():
                logger.error("Cannot start consuming - no connection")
                return False
        
        try:
            # Set up consumer
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue=settings.rabbitmq_queue,
                on_message_callback=self.process_message
            )
            
            self.consuming = True
            logger.info("Started consuming messages from RabbitMQ")
            
            # Start consuming (this blocks)
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("Stopping consumer...")
            self.stop_consuming()
        except Exception as e:
            logger.error(f"Error during consuming: {e}")
            self.consuming = False
    
    def stop_consuming(self):
        """Stop consuming messages"""
        if self.consuming and self.channel:
            self.channel.stop_consuming()
            self.consuming = False
            logger.info("Stopped consuming messages")
    
    def close(self):
        """Close connection"""
        try:
            if self.consuming:
                self.stop_consuming()
            
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                logger.info("RabbitMQ connection closed")
                
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}")
    
    def publish_message(self, event_type: str, data: Dict[str, Any]):
        """Publish a message to RabbitMQ (for testing)"""
        if not self.connection or self.connection.is_closed:
            if not self.connect():
                logger.error("Cannot publish - no connection")
                return False
        
        try:
            message = {
                'event_type': event_type,
                'data': data,
                'timestamp': asyncio.get_event_loop().time()
            }
            
            self.channel.basic_publish(
                exchange=settings.rabbitmq_exchange,
                routing_key=settings.rabbitmq_routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            
            logger.info(f"Published {event_type} event")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            return False


# Global consumer instance
rabbitmq_consumer = RabbitMQConsumer()