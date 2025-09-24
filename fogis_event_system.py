#!/usr/bin/env python3
"""
FOGIS Event-Driven System

This module provides the complete event-driven architecture for FOGIS services,
implementing publish-subscribe pattern with Redis for scalable inter-service communication.

Author: System Architecture Team
Date: 2025-09-21
Issue: Event-driven architecture for FOGIS ecosystem
"""

import json
import logging
import redis
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

# Set up logging
logger = logging.getLogger(__name__)

class EventType(Enum):
    """Standardized event types for FOGIS system."""
    
    # Match events
    MATCHES_UPDATED = "matches.updated"
    MATCHES_ADDED = "matches.added"
    MATCHES_REMOVED = "matches.removed"
    MATCHES_TIME_CHANGED = "matches.time_changed"
    MATCHES_VENUE_CHANGED = "matches.venue_changed"
    MATCHES_STATUS_CHANGED = "matches.status_changed"
    MATCHES_ALL = "matches.all"
    
    # System events
    SYSTEM_HEALTH = "system.health"
    SYSTEM_ERROR = "system.error"
    
    # Service events
    SERVICE_STARTED = "service.started"
    SERVICE_STOPPED = "service.stopped"
    SERVICE_ERROR = "service.error"

@dataclass
class FOGISEvent:
    """Standardized FOGIS event structure."""
    
    event_type: str
    data: Any
    timestamp: str
    source: str
    metadata: Dict[str, Any]
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FOGISEvent':
        """Create event from dictionary."""
        return cls(**data)

class RedisConnectionManager:
    """Manages Redis connections with health checking and reconnection logic."""
    
    def __init__(self, redis_url: str = "redis://redis:6379", **kwargs):
        """Initialize Redis connection manager."""
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
        """Get Redis client with automatic health checking."""
        current_time = time.time()
        
        if (self._client is None or 
            current_time - self._last_health_check > self._health_check_interval):
            
            if not self._check_connection_health():
                self._reconnect()
            
            self._last_health_check = current_time
        
        return self._client
    
    def _check_connection_health(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            if self._client is None:
                return False
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
            self._client.ping()
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._client = None
            raise

class FOGISEventPublisher:
    """Publishes standardized events to Redis pub/sub channels."""
    
    def __init__(self, connection_manager: RedisConnectionManager, source_name: str):
        """Initialize event publisher."""
        self.connection_manager = connection_manager
        self.source_name = source_name
        self.previous_matches = {}
        
    def publish_event(self, event_type: str, data: Any, metadata: Optional[Dict] = None) -> bool:
        """Publish standardized event to Redis."""
        try:
            # Create standardized event
            event = FOGISEvent(
                event_type=event_type,
                data=data,
                timestamp=datetime.now().isoformat(),
                source=self.source_name,
                metadata=metadata or {},
                version="1.0"
            )
            
            event_json = json.dumps(event.to_dict(), default=str)
            
            # Publish to multiple channels for different consumption patterns
            channels = [
                'fogis.events.all',  # All events
                f'fogis.events.{event_type}',  # Specific event type
            ]
            
            # Add to specific channels based on event type
            if event_type.startswith('matches.'):
                channels.append('fogis.matches.all')
            
            published_count = 0
            client = self.connection_manager.client
            
            for channel in channels:
                subscribers = client.publish(channel, event_json)
                published_count += subscribers
                logger.debug(f"Published {event_type} to {channel}: {subscribers} subscribers")
            
            # Store in Redis Stream for durability and replay
            stream_key = f"fogis:events:{event_type.split('.')[0]}"
            # Convert event data to JSON strings for Redis Stream
            stream_data = {k: json.dumps(v, default=str) if not isinstance(v, str) else v
                          for k, v in event.to_dict().items()}
            client.xadd(stream_key, stream_data, maxlen=1000)  # Keep last 1000 events
            
            logger.info(f"Event published: {event_type} to {len(channels)} channels, {published_count} total subscribers")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            return False
    
    def publish_match_events(self, matches: List[Dict], metadata: Optional[Dict] = None) -> bool:
        """Publish match events with change detection."""
        try:
            # Detect changes
            changes = self._detect_match_changes(matches)
            
            # Prepare metadata
            event_metadata = {
                'total_matches': len(matches),
                'changes_detected': sum(len(change_list) for change_list in changes.values()),
                'processing_timestamp': datetime.now().isoformat(),
                **(metadata or {})
            }
            
            # Publish specific change events
            events_published = 0
            
            if changes['added']:
                self.publish_event(EventType.MATCHES_ADDED.value, changes['added'], 
                                 {**event_metadata, 'change_type': 'added'})
                events_published += 1
            
            if changes['updated']:
                self.publish_event(EventType.MATCHES_UPDATED.value, changes['updated'], 
                                 {**event_metadata, 'change_type': 'updated'})
                events_published += 1
            
            if changes['removed']:
                self.publish_event(EventType.MATCHES_REMOVED.value, changes['removed'], 
                                 {**event_metadata, 'change_type': 'removed'})
                events_published += 1
            
            # Always publish complete match state
            self.publish_event(EventType.MATCHES_ALL.value, matches, event_metadata)
            events_published += 1
            
            logger.info(f"Published {events_published} match events from {self.source_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish match events from {self.source_name}: {e}")
            return False
    
    def _detect_match_changes(self, current_matches: List[Dict]) -> Dict[str, List[Dict]]:
        """Detect changes between current and previous match data."""
        current_by_id = {str(match.get('matchid')): match for match in current_matches}
        previous_by_id = self.previous_matches
        
        changes = {
            'added': [],
            'updated': [],
            'removed': []
        }
        
        # Find added matches
        for match_id, match in current_by_id.items():
            if match_id not in previous_by_id:
                changes['added'].append(match)
                logger.debug(f"New match detected: {match_id}")
        
        # Find updated matches
        for match_id, current_match in current_by_id.items():
            if match_id in previous_by_id:
                previous_match = previous_by_id[match_id]
                if self._match_changed(previous_match, current_match):
                    changes['updated'].append(current_match)
                    logger.debug(f"Match updated: {match_id}")
        
        # Find removed matches
        for match_id, match in previous_by_id.items():
            if match_id not in current_by_id:
                changes['removed'].append(match)
                logger.debug(f"Match removed: {match_id}")
        
        # Update previous matches for next comparison
        self.previous_matches = current_by_id.copy()
        
        return changes
    
    def _match_changed(self, previous: Dict, current: Dict) -> bool:
        """Check if any match data changed."""
        key_fields = ['speldatum', 'avsparkstid', 'lag1namn', 'lag2namn', 
                     'anlaggningnamn', 'status', 'referee_assignments']
        
        for field in key_fields:
            if previous.get(field) != current.get(field):
                return True
        
        return False

class FOGISEventSubscriber:
    """Subscribes to Redis pub/sub channels and processes events."""
    
    def __init__(self, connection_manager: RedisConnectionManager, service_name: str):
        """Initialize event subscriber."""
        self.connection_manager = connection_manager
        self.service_name = service_name
        self.event_handlers: Dict[str, Callable] = {}
        self.running = False
        self.subscription_thread: Optional[threading.Thread] = None
        
    def register_handler(self, event_type: str, handler: Callable[[FOGISEvent], None]):
        """Register event handler for specific event type."""
        self.event_handlers[event_type] = handler
        logger.info(f"Registered handler for {event_type} in {self.service_name}")
    
    def register_match_handler(self, handler: Callable[[List[Dict], Dict], None]):
        """Register handler for all match events."""
        def event_handler(event: FOGISEvent):
            matches = event.data if isinstance(event.data, list) else []
            metadata = event.metadata
            handler(matches, metadata)
        
        # Register for all match event types
        for event_type in [e.value for e in EventType if e.value.startswith('matches.')]:
            self.register_handler(event_type, event_handler)
    
    def start_subscription(self, channels: Optional[List[str]] = None):
        """Start event subscription in background thread."""
        if channels is None:
            channels = ['fogis.matches.all', 'fogis.events.all']
        
        def subscription_worker():
            try:
                self._subscribe_to_channels(channels)
            except Exception as e:
                logger.error(f"Subscription worker failed for {self.service_name}: {e}")
        
        self.subscription_thread = threading.Thread(
            target=subscription_worker,
            name=f"{self.service_name}-event-subscriber",
            daemon=True
        )
        self.subscription_thread.start()
        
        logger.info(f"Started event subscription for {self.service_name}")
    
    def _subscribe_to_channels(self, channels: List[str]):
        """Subscribe to Redis pub/sub channels and process events."""
        try:
            client = self.connection_manager.client
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
        """Handle incoming pub/sub message."""
        try:
            # Parse event data
            event_data = json.loads(message['data'])
            event = FOGISEvent.from_dict(event_data)
            
            logger.debug(f"{self.service_name} received event: {event.event_type}")
            
            # Find and execute handler
            handler = self.event_handlers.get(event.event_type)
            if handler:
                handler(event)
                logger.debug(f"Event {event.event_type} processed by {self.service_name}")
            else:
                logger.debug(f"No handler for event type {event.event_type} in {self.service_name}")
                
        except Exception as e:
            logger.error(f"Failed to handle message in {self.service_name}: {e}")
    
    def stop(self):
        """Stop event subscription."""
        self.running = False
        logger.info(f"Stopping event subscription for {self.service_name}")

def setup_event_system(service_name: str, redis_url: str = "redis://redis:6379"):
    """
    Setup complete event-driven architecture for a FOGIS service.
    
    Returns:
        Tuple of (publisher, subscriber, connection_manager)
    """
    # Initialize Redis connection
    connection_manager = RedisConnectionManager(redis_url)
    
    # Initialize publisher and subscriber
    publisher = FOGISEventPublisher(connection_manager, service_name)
    subscriber = FOGISEventSubscriber(connection_manager, service_name)
    
    logger.info(f"Event-driven architecture setup completed for {service_name}")
    
    return publisher, subscriber, connection_manager

# Test function
def test_event_system():
    """Test the event system functionality."""
    logger.info("FOGIS Event System module loaded successfully")
    logger.info("Use setup_event_system(service_name) to initialize event architecture")
    return True

if __name__ == "__main__":
    test_event_system()
