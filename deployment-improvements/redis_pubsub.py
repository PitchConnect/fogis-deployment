#!/usr/bin/env python3
"""
Minimal Redis Pub/Sub for FOGIS Services

This module provides the minimal Redis pub/sub functionality requested
for communication between match-list-processor and calendar service.

Integrates with existing FOGIS deployment infrastructure.

Author: System Architecture Team
Date: 2025-09-21
Issue: Redis pub/sub integration with existing deployment system
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Callable, Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class FOGISRedisPubSub:
    """Minimal Redis pub/sub client for FOGIS services."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis pub/sub client."""
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://redis:6379')
        self.client = None
        self._connect()
    
    def _connect(self):
        """Connect to Redis with error handling."""
        try:
            import redis
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            # Test connection
            self.client.ping()
            logger.info(f"✅ Connected to Redis: {self.redis_url}")
        except ImportError:
            logger.error("❌ Redis package not installed. Run: pip install redis")
            self.client = None
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Redis is available."""
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except Exception:
            return False
    
    def publish_matches(self, matches: List[Dict], source: str = "match-list-processor") -> bool:
        """
        Publish match data to Redis.
        
        Args:
            matches: List of match dictionaries
            source: Source service name
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        if not self.is_available():
            logger.warning("Redis not available for publishing")
            return False
        
        try:
            message = {
                'matches': matches,
                'timestamp': datetime.now().isoformat(),
                'source': source,
                'count': len(matches)
            }
            
            # Publish to main channel
            subscribers = self.client.publish('fogis_matches', json.dumps(message))
            
            logger.info(f"📡 Published {len(matches)} matches to Redis ({subscribers} subscribers)")
            
            # Log target match if present (for debugging)
            target_match = next((m for m in matches if m.get('speldatum') == '2025-09-23'), None)
            if target_match:
                logger.info(f"🎯 Target match included: {target_match.get('lag1namn')} vs {target_match.get('lag2namn')}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to publish matches to Redis: {e}")
            return False
    
    def subscribe_to_matches(self, handler: Callable[[List[Dict], Dict], None]) -> bool:
        """
        Subscribe to match events from Redis.
        
        Args:
            handler: Function to call with (matches, metadata) when events received
            
        Returns:
            bool: True if subscription started successfully
        """
        if not self.is_available():
            logger.warning("Redis not available for subscription")
            return False
        
        def subscription_worker():
            """Background worker for Redis subscription."""
            try:
                pubsub = self.client.pubsub()
                pubsub.subscribe('fogis_matches')
                
                logger.info("📡 Started Redis subscription for match events")
                
                for message in pubsub.listen():
                    if message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])
                            matches = data.get('matches', [])
                            metadata = {
                                'timestamp': data.get('timestamp'),
                                'source': data.get('source'),
                                'count': data.get('count', len(matches))
                            }
                            
                            logger.info(f"📅 Received {len(matches)} matches from Redis")
                            
                            # Call handler
                            handler(matches, metadata)
                            
                        except Exception as e:
                            logger.error(f"❌ Failed to process Redis message: {e}")
                            
            except Exception as e:
                logger.error(f"❌ Redis subscription failed: {e}")
        
        try:
            # Start subscription in background thread
            thread = threading.Thread(target=subscription_worker, daemon=True, name="redis-subscriber")
            thread.start()
            
            # Give it a moment to start
            time.sleep(1)
            
            logger.info("✅ Redis subscription started in background")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start Redis subscription: {e}")
            return False
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test Redis connection and return status.
        
        Returns:
            Dict with connection status and details
        """
        if not self.client:
            return {
                'available': False,
                'error': 'Redis client not initialized',
                'url': self.redis_url
            }
        
        try:
            # Test basic connection
            self.client.ping()
            
            # Test pub/sub functionality
            test_channel = 'fogis_test'
            test_message = {'test': True, 'timestamp': datetime.now().isoformat()}
            
            subscribers = self.client.publish(test_channel, json.dumps(test_message))
            
            return {
                'available': True,
                'url': self.redis_url,
                'ping': 'OK',
                'pub_sub': 'OK',
                'test_subscribers': subscribers
            }
            
        except Exception as e:
            return {
                'available': False,
                'error': str(e),
                'url': self.redis_url
            }

def setup_match_processor_pubsub(matches: List[Dict]) -> bool:
    """
    Helper function for match processor to publish matches.
    
    Args:
        matches: List of match dictionaries
        
    Returns:
        bool: True if published successfully
    """
    redis_client = FOGISRedisPubSub()
    return redis_client.publish_matches(matches, "match-list-processor")

def setup_calendar_service_pubsub(sync_handler: Callable[[List[Dict]], None]) -> bool:
    """
    Helper function for calendar service to subscribe to matches.
    
    Args:
        sync_handler: Function to call with matches for calendar sync
        
    Returns:
        bool: True if subscription started successfully
    """
    def event_handler(matches: List[Dict], metadata: Dict):
        """Wrapper to call sync handler with just matches."""
        sync_handler(matches)
    
    redis_client = FOGISRedisPubSub()
    return redis_client.subscribe_to_matches(event_handler)

def test_redis_pubsub() -> bool:
    """
    Test Redis pub/sub functionality.
    
    Returns:
        bool: True if test successful
    """
    logger.info("🧪 Testing Redis pub/sub functionality...")
    
    redis_client = FOGISRedisPubSub()
    
    # Test connection
    status = redis_client.test_connection()
    if not status['available']:
        logger.error(f"❌ Redis connection test failed: {status['error']}")
        return False
    
    logger.info("✅ Redis pub/sub test successful")
    logger.info(f"   URL: {status['url']}")
    logger.info(f"   Ping: {status['ping']}")
    logger.info(f"   Pub/Sub: {status['pub_sub']}")
    
    return True

if __name__ == "__main__":
    # Test the module
    test_redis_pubsub()
