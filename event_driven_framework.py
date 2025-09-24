"""
Event-Driven Framework for FOGIS Service Integration

This module provides the complete event-driven framework for FOGIS services,
implementing the publish-subscribe pattern with standardized event formats.

Author: System Architecture Team
Date: 2025-09-19
Issue: Event-driven architecture implementation
"""

import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from redis_infrastructure_setup import RedisConnectionManager, EventPublisher, EventSubscriber

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
    
    # System events
    SYSTEM_HEALTH = "system.health"
    SYSTEM_ERROR = "system.error"
    
    # Service events
    SERVICE_STARTED = "service.started"
    SERVICE_STOPPED = "service.stopped"
    SERVICE_ERROR = "service.error"


@dataclass
class MatchEvent:
    """Standardized match event data structure."""
    
    event_type: str
    matches: List[Dict[str, Any]]
    timestamp: str
    source: str
    metadata: Dict[str, Any]
    changes: Optional[List[Dict[str, Any]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class MatchChangeDetector:
    """Detects changes in match data for targeted event publishing."""
    
    def __init__(self):
        """Initialize change detector."""
        self.previous_matches: Dict[str, Dict] = {}
        
    def detect_changes(self, current_matches: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Detect changes between current and previous match data.
        
        Args:
            current_matches: Current match data
            
        Returns:
            Dict containing added, updated, removed, and changed matches
        """
        current_by_id = {str(match.get('matchid')): match for match in current_matches}
        previous_by_id = self.previous_matches
        
        changes = {
            'added': [],
            'updated': [],
            'removed': [],
            'time_changed': [],
            'venue_changed': [],
            'status_changed': []
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
                
                # Check for specific types of changes
                if self._time_changed(previous_match, current_match):
                    changes['time_changed'].append(current_match)
                    logger.debug(f"Time change detected for match {match_id}")
                
                if self._venue_changed(previous_match, current_match):
                    changes['venue_changed'].append(current_match)
                    logger.debug(f"Venue change detected for match {match_id}")
                
                if self._status_changed(previous_match, current_match):
                    changes['status_changed'].append(current_match)
                    logger.debug(f"Status change detected for match {match_id}")
                
                # General update check
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
    
    def _time_changed(self, previous: Dict, current: Dict) -> bool:
        """Check if match time changed."""
        return (previous.get('speldatum') != current.get('speldatum') or
                previous.get('avsparkstid') != current.get('avsparkstid'))
    
    def _venue_changed(self, previous: Dict, current: Dict) -> bool:
        """Check if match venue changed."""
        return previous.get('anlaggningnamn') != current.get('anlaggningnamn')
    
    def _status_changed(self, previous: Dict, current: Dict) -> bool:
        """Check if match status changed."""
        return previous.get('status') != current.get('status')
    
    def _match_changed(self, previous: Dict, current: Dict) -> bool:
        """Check if any match data changed."""
        # Compare key fields
        key_fields = ['speldatum', 'avsparkstid', 'lag1namn', 'lag2namn', 
                     'anlaggningnamn', 'status', 'referee_assignments']
        
        for field in key_fields:
            if previous.get(field) != current.get(field):
                return True
        
        return False


class FOGISEventPublisher:
    """Enhanced event publisher for FOGIS match data."""
    
    def __init__(self, connection_manager: RedisConnectionManager, source_name: str):
        """
        Initialize FOGIS event publisher.
        
        Args:
            connection_manager: Redis connection manager
            source_name: Name of the publishing service
        """
        self.publisher = EventPublisher(connection_manager)
        self.source_name = source_name
        self.change_detector = MatchChangeDetector()
        
    def publish_match_updates(self, matches: List[Dict], metadata: Optional[Dict] = None) -> bool:
        """
        Publish match updates with change detection.
        
        Args:
            matches: Current match data
            metadata: Optional metadata
            
        Returns:
            bool: True if published successfully
        """
        try:
            # Detect changes
            changes = self.change_detector.detect_changes(matches)
            
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
                self.publisher.publish_match_events(
                    EventType.MATCHES_ADDED.value, 
                    changes['added'], 
                    {**event_metadata, 'change_type': 'added'}
                )
                events_published += 1
            
            if changes['updated']:
                self.publisher.publish_match_events(
                    EventType.MATCHES_UPDATED.value, 
                    changes['updated'], 
                    {**event_metadata, 'change_type': 'updated'}
                )
                events_published += 1
            
            if changes['removed']:
                self.publisher.publish_match_events(
                    EventType.MATCHES_REMOVED.value, 
                    changes['removed'], 
                    {**event_metadata, 'change_type': 'removed'}
                )
                events_published += 1
            
            if changes['time_changed']:
                self.publisher.publish_match_events(
                    EventType.MATCHES_TIME_CHANGED.value, 
                    changes['time_changed'], 
                    {**event_metadata, 'change_type': 'time_changed'}
                )
                events_published += 1
            
            if changes['venue_changed']:
                self.publisher.publish_match_events(
                    EventType.MATCHES_VENUE_CHANGED.value, 
                    changes['venue_changed'], 
                    {**event_metadata, 'change_type': 'venue_changed'}
                )
                events_published += 1
            
            if changes['status_changed']:
                self.publisher.publish_match_events(
                    EventType.MATCHES_STATUS_CHANGED.value, 
                    changes['status_changed'], 
                    {**event_metadata, 'change_type': 'status_changed'}
                )
                events_published += 1
            
            # Always publish complete match state
            self.publisher.publish_match_events(
                "matches.all", 
                matches, 
                event_metadata
            )
            events_published += 1
            
            logger.info(f"Published {events_published} match events from {self.source_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish match updates from {self.source_name}: {e}")
            return False


class FOGISEventSubscriber:
    """Enhanced event subscriber for FOGIS services."""
    
    def __init__(self, connection_manager: RedisConnectionManager, service_name: str):
        """
        Initialize FOGIS event subscriber.
        
        Args:
            connection_manager: Redis connection manager
            service_name: Name of the subscribing service
        """
        self.subscriber = EventSubscriber(connection_manager, service_name)
        self.service_name = service_name
        self.subscription_thread: Optional[threading.Thread] = None
        
    def register_match_handler(self, handler: Callable[[List[Dict], Dict], None]):
        """
        Register handler for all match events.
        
        Args:
            handler: Function that accepts (matches, metadata)
        """
        def event_handler(event_data: Dict):
            matches = event_data.get('data', [])
            metadata = event_data.get('metadata', {})
            handler(matches, metadata)
        
        # Register for all match event types
        for event_type in [e.value for e in EventType if e.value.startswith('matches.')]:
            self.subscriber.register_handler(event_type, event_handler)
    
    def register_specific_handler(self, event_type: EventType, handler: Callable[[List[Dict], Dict], None]):
        """
        Register handler for specific event type.
        
        Args:
            event_type: Specific event type to handle
            handler: Function that accepts (matches, metadata)
        """
        def event_handler(event_data: Dict):
            matches = event_data.get('data', [])
            metadata = event_data.get('metadata', {})
            handler(matches, metadata)
        
        self.subscriber.register_handler(event_type.value, event_handler)
    
    def start_subscription(self, channels: Optional[List[str]] = None):
        """
        Start event subscription in background thread.
        
        Args:
            channels: List of channels to subscribe to (default: all match events)
        """
        if channels is None:
            channels = ['fogis.matches.all', 'fogis.events.all']
        
        def subscription_worker():
            try:
                self.subscriber.subscribe_to_channels(channels)
            except Exception as e:
                logger.error(f"Subscription worker failed for {self.service_name}: {e}")
        
        self.subscription_thread = threading.Thread(
            target=subscription_worker,
            name=f"{self.service_name}-event-subscriber",
            daemon=True
        )
        self.subscription_thread.start()
        
        logger.info(f"Started event subscription for {self.service_name}")
    
    def stop_subscription(self):
        """Stop event subscription."""
        if self.subscriber:
            self.subscriber.stop()
        
        if self.subscription_thread and self.subscription_thread.is_alive():
            self.subscription_thread.join(timeout=5)
        
        logger.info(f"Stopped event subscription for {self.service_name}")


def setup_event_driven_architecture(service_name: str, redis_url: str = "redis://redis:6379"):
    """
    Setup complete event-driven architecture for a FOGIS service.
    
    Args:
        service_name: Name of the service
        redis_url: Redis connection URL
        
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


# Example integration for match-list-processor
def integrate_match_processor_events(existing_processor, redis_url: str = "redis://redis:6379"):
    """
    Integrate event publishing into existing match processor.
    
    Args:
        existing_processor: Existing match processor instance
        redis_url: Redis connection URL
        
    Returns:
        Enhanced processor function
    """
    publisher, _, _ = setup_event_driven_architecture("match-list-processor", redis_url)
    
    def enhanced_processor():
        try:
            # Get matches from existing processor
            matches = existing_processor.fetch_and_process_matches()
            
            # Publish events
            publisher.publish_match_updates(matches)
            
            # Keep existing notifications during transition
            existing_processor.notify_services(matches)
            
            return matches
            
        except Exception as e:
            logger.error(f"Enhanced match processor failed: {e}")
            raise
    
    return enhanced_processor


# Example integration for calendar service
def integrate_calendar_service_events(existing_calendar_handler, redis_url: str = "redis://redis:6379"):
    """
    Integrate event subscription into existing calendar service.
    
    Args:
        existing_calendar_handler: Existing calendar handler
        redis_url: Redis connection URL
        
    Returns:
        Event subscriber instance
    """
    _, subscriber, _ = setup_event_driven_architecture("calendar-service", redis_url)
    
    def handle_match_events(matches: List[Dict], metadata: Dict):
        """Handle incoming match events."""
        try:
            logger.info(f"Received {len(matches)} matches via events")
            
            # Use existing calendar sync logic
            existing_calendar_handler.sync_matches_to_calendar(matches)
            
        except Exception as e:
            logger.error(f"Event-driven calendar sync failed: {e}")
    
    # Register event handler
    subscriber.register_match_handler(handle_match_events)
    
    # Start subscription
    subscriber.start_subscription()
    
    return subscriber


if __name__ == "__main__":
    logger.info("Event-driven framework module loaded")
    logger.info("Use setup_event_driven_architecture() to initialize event system")
