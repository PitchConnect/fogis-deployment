"""
Redis Infrastructure Setup for Event-Driven FOGIS Architecture

This module provides Redis infrastructure setup and client management
for the event-driven publish-subscribe pattern implementation.

Author: System Architecture Team
Date: 2025-09-19
Issue: Event-driven architecture foundation
"""

import json
import logging
import redis
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class RedisConnectionManager:
    """
    Manages Redis connections with health checking and reconnection logic.
    """
    
    def __init__(self, redis_url: str = "redis://redis:6379", **kwargs):
        """
        Initialize Redis connection manager.
        
        Args:
            redis_url: Redis connection URL
            **kwargs: Additional Redis client parameters
        """
        self.redis_url = redis_url
        self.client_kwargs = kwargs
        self.client_kwargs.setdefault('decode_responses', True)
        self.client_kwargs.setdefault('socket_connect_timeout', 5)
        self.client_kwargs.setdefault('socket_timeout', 5)
        self.client_kwargs.setdefault('retry_on_timeout', True)
        
        self._client = None
        self._last_health_check = 0
        self._health_check_interval = 30  # seconds
        
    @property
    def client(self) -> redis.Redis:
        """
        Get Redis client with automatic health checking.
        
        Returns:
            redis.Redis: Connected Redis client
        """
        current_time = time.time()
        
        # Check if we need to verify connection health
        if (self._client is None or 
            current_time - self._last_health_check > self._health_check_interval):
            
            if not self._check_connection_health():
                self._reconnect()
            
            self._last_health_check = current_time
        
        return self._client
    
    def _check_connection_health(self) -> bool:
        """
        Check if Redis connection is healthy.
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            if self._client is None:
                return False
                
            # Simple ping test
            self._client.ping()
            return True
            
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return False
    
    def _reconnect(self):
        """Reconnect to Redis."""
        try:
            logger.info(f"Connecting to Redis: {self.redis_url}")
            self._client = redis.from_url(self.redis_url, **self.client_kwargs)
            
            # Test connection
            self._client.ping()
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._client = None
            raise
    
    @contextmanager
    def get_client(self):
        """
        Context manager for Redis client.
        
        Yields:
            redis.Redis: Connected Redis client
        """
        try:
            yield self.client
        except Exception as e:
            logger.error(f"Redis operation failed: {e}")
            # Force reconnection on next access
            self._client = None
            raise


class EventPublisher:
    """
    Publishes standardized events to Redis pub/sub channels.
    """
    
    def __init__(self, connection_manager: RedisConnectionManager):
        """
        Initialize event publisher.
        
        Args:
            connection_manager: Redis connection manager
        """
        self.connection_manager = connection_manager
        
    def publish_event(self, event_type: str, data: Any, metadata: Optional[Dict] = None) -> bool:
        """
        Publish standardized event to Redis.
        
        Args:
            event_type: Type of event (e.g., 'matches.updated')
            data: Event data payload
            metadata: Optional metadata
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        try:
            # Create standardized event structure
            event = {
                'event_type': event_type,
                'timestamp': datetime.now().isoformat(),
                'data': data,
                'metadata': metadata or {},
                'source': 'fogis-system',
                'version': '1.0'
            }
            
            event_json = json.dumps(event, default=str)
            
            with self.connection_manager.get_client() as client:
                # Publish to multiple channels for different consumption patterns
                channels = [
                    'fogis.events.all',  # All events
                    f'fogis.events.{event_type}',  # Specific event type
                ]
                
                # Add to specific channels based on event type
                if event_type.startswith('matches.'):
                    channels.append('fogis.matches.all')
                
                published_count = 0
                for channel in channels:
                    subscribers = client.publish(channel, event_json)
                    published_count += subscribers
                    logger.debug(f"Published {event_type} to {channel}: {subscribers} subscribers")
                
                # Store in Redis Stream for durability and replay
                stream_key = f"fogis:events:{event_type.split('.')[0]}"
                client.xadd(stream_key, event, maxlen=1000)  # Keep last 1000 events
                
                logger.info(f"Event published: {event_type} to {len(channels)} channels, {published_count} total subscribers")
                return True
                
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            return False
    
    def publish_match_events(self, event_type: str, matches: List[Dict], metadata: Optional[Dict] = None) -> bool:
        """
        Publish match-specific events.
        
        Args:
            event_type: Match event type ('matches.updated', 'matches.added', etc.)
            matches: List of match data
            metadata: Optional metadata
            
        Returns:
            bool: True if published successfully
        """
        match_metadata = {
            'match_count': len(matches),
            'processing_timestamp': datetime.now().isoformat(),
            **(metadata or {})
        }
        
        return self.publish_event(event_type, matches, match_metadata)


class EventSubscriber:
    """
    Subscribes to Redis pub/sub channels and processes events.
    """
    
    def __init__(self, connection_manager: RedisConnectionManager, service_name: str):
        """
        Initialize event subscriber.
        
        Args:
            connection_manager: Redis connection manager
            service_name: Name of subscribing service
        """
        self.connection_manager = connection_manager
        self.service_name = service_name
        self.event_handlers: Dict[str, Callable] = {}
        self.running = False
        
    def register_handler(self, event_type: str, handler: Callable[[Dict], None]):
        """
        Register event handler for specific event type.
        
        Args:
            event_type: Event type to handle
            handler: Function to handle the event
        """
        self.event_handlers[event_type] = handler
        logger.info(f"Registered handler for {event_type} in {self.service_name}")
    
    def subscribe_to_channels(self, channels: List[str]):
        """
        Subscribe to Redis pub/sub channels and process events.
        
        Args:
            channels: List of channels to subscribe to
        """
        try:
            with self.connection_manager.get_client() as client:
                pubsub = client.pubsub()
                
                # Subscribe to channels
                for channel in channels:
                    pubsub.subscribe(channel)
                    logger.info(f"{self.service_name} subscribed to {channel}")
                
                self.running = True
                logger.info(f"{self.service_name} event subscription started")
                
                # Process messages
                for message in pubsub.listen():
                    if not self.running:
                        break
                        
                    if message['type'] == 'message':
                        self._handle_message(message)
                        
        except Exception as e:
            logger.error(f"Event subscription failed for {self.service_name}: {e}")
            raise
        finally:
            self.running = False
            logger.info(f"{self.service_name} event subscription stopped")
    
    def _handle_message(self, message: Dict):
        """
        Handle incoming pub/sub message.
        
        Args:
            message: Redis pub/sub message
        """
        try:
            # Parse event data
            event_data = json.loads(message['data'])
            event_type = event_data.get('event_type')
            
            logger.debug(f"{self.service_name} received event: {event_type}")
            
            # Find and execute handler
            handler = self.event_handlers.get(event_type)
            if handler:
                handler(event_data)
                logger.debug(f"Event {event_type} processed by {self.service_name}")
            else:
                logger.debug(f"No handler for event type {event_type} in {self.service_name}")
                
        except Exception as e:
            logger.error(f"Failed to handle message in {self.service_name}: {e}")
    
    def stop(self):
        """Stop event subscription."""
        self.running = False
        logger.info(f"Stopping event subscription for {self.service_name}")


class RedisHealthChecker:
    """
    Provides health checking capabilities for Redis infrastructure.
    """
    
    def __init__(self, connection_manager: RedisConnectionManager):
        """
        Initialize health checker.
        
        Args:
            connection_manager: Redis connection manager
        """
        self.connection_manager = connection_manager
    
    def check_redis_health(self) -> Dict[str, Any]:
        """
        Comprehensive Redis health check.
        
        Returns:
            Dict containing health status and metrics
        """
        health_data = {
            'status': 'unknown',
            'timestamp': datetime.now().isoformat(),
            'connection': False,
            'pub_sub': False,
            'streams': False,
            'memory_usage': None,
            'connected_clients': None,
            'error': None
        }
        
        try:
            with self.connection_manager.get_client() as client:
                # Basic connection test
                client.ping()
                health_data['connection'] = True
                
                # Pub/sub test
                test_channel = 'fogis.health.test'
                subscribers = client.publish(test_channel, 'health_check')
                health_data['pub_sub'] = True
                
                # Streams test
                test_stream = 'fogis:health:test'
                client.xadd(test_stream, {'test': 'health_check'}, maxlen=1)
                health_data['streams'] = True
                
                # Get Redis info
                info = client.info()
                health_data['memory_usage'] = info.get('used_memory_human')
                health_data['connected_clients'] = info.get('connected_clients')
                
                health_data['status'] = 'healthy'
                
        except Exception as e:
            health_data['status'] = 'unhealthy'
            health_data['error'] = str(e)
            logger.error(f"Redis health check failed: {e}")
        
        return health_data


# Docker Compose configuration for Redis
DOCKER_COMPOSE_REDIS_CONFIG = """
# Add this to your docker-compose.yml

services:
  redis:
    image: redis:7-alpine
    container_name: fogis-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
      start_period: 10s
    restart: unless-stopped
    networks:
      - fogis-network

volumes:
  redis_data:
    driver: local

networks:
  fogis-network:
    driver: bridge
"""

# Environment variables for services
ENVIRONMENT_VARIABLES = """
# Add these environment variables to your services

# For all services using Redis
REDIS_URL=redis://redis:6379

# For event publishing services
EVENT_PUBLISHING_ENABLED=true
REDIS_PUBLISH_TIMEOUT=5

# For event subscribing services  
EVENT_SUBSCRIPTION_ENABLED=true
REDIS_SUBSCRIBE_CHANNELS=fogis.matches.all,fogis.events.all
"""


def setup_redis_infrastructure():
    """
    Setup Redis infrastructure with proper configuration.
    
    Returns:
        Tuple of (connection_manager, publisher, health_checker)
    """
    # Initialize connection manager
    connection_manager = RedisConnectionManager()
    
    # Initialize publisher
    publisher = EventPublisher(connection_manager)
    
    # Initialize health checker
    health_checker = RedisHealthChecker(connection_manager)
    
    # Test initial connection
    health_status = health_checker.check_redis_health()
    if health_status['status'] != 'healthy':
        logger.warning(f"Redis health check failed: {health_status}")
    else:
        logger.info("Redis infrastructure setup completed successfully")
    
    return connection_manager, publisher, health_checker


if __name__ == "__main__":
    # Example usage
    logger.info("Redis infrastructure module loaded")
    logger.info("Use setup_redis_infrastructure() to initialize Redis components")
    
    # Print configuration examples
    print("\n=== Docker Compose Configuration ===")
    print(DOCKER_COMPOSE_REDIS_CONFIG)
    
    print("\n=== Environment Variables ===")
    print(ENVIRONMENT_VARIABLES)
