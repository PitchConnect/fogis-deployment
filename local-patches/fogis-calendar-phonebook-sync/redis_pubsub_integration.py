#!/usr/bin/env python3
"""
Redis Pub/Sub Integration for Calendar Service

This module provides minimal Redis pub/sub functionality for the calendar service
to subscribe to match updates from the match-list-processor and trigger calendar sync.

Author: System Architecture Team
Date: 2025-09-21
Issue: Redis pub/sub integration for calendar service
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger(__name__)

class CalendarServiceRedisPubSub:
    """Minimal Redis pub/sub client for calendar service."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis pub/sub client."""
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://redis:6379')
        self.client = None
        self.pubsub = None
        self.subscription_thread = None
        self.running = False
        self.enabled = os.getenv('REDIS_PUBSUB_ENABLED', 'true').lower() == 'true'
        
        if self.enabled:
            self._connect()
    
    def _connect(self):
        """Connect to Redis with error handling."""
        try:
            import redis
            self.client = redis.from_url(self.redis_url, decode_responses=True, socket_connect_timeout=5)
            # Test connection
            self.client.ping()
            logger.info(f"✅ Calendar service connected to Redis: {self.redis_url}")
        except ImportError:
            logger.warning("⚠️ Redis package not installed - pub/sub disabled, using HTTP endpoints only")
            self.client = None
            self.enabled = False
        except Exception as e:
            logger.warning(f"⚠️ Failed to connect to Redis: {e} - using HTTP endpoints only")
            self.client = None
            self.enabled = False
    
    def is_available(self) -> bool:
        """Check if Redis is available."""
        if not self.enabled or not self.client:
            return False
        try:
            self.client.ping()
            return True
        except Exception:
            return False
    
    def subscribe_to_match_updates(self, handler: Callable[[List[Dict], Dict], None]) -> bool:
        """
        Subscribe to match updates from Redis.
        
        Args:
            handler: Function to call with (matches, metadata) when updates received
            
        Returns:
            bool: True if subscription started successfully
        """
        if not self.is_available():
            logger.info("Redis not available for subscription - calendar service will use HTTP endpoints only")
            return False
        
        def subscription_worker():
            """Background worker for Redis subscription."""
            try:
                self.pubsub = self.client.pubsub()
                self.pubsub.subscribe('fogis_matches')
                
                logger.info("📡 Calendar service subscribed to Redis match updates")
                
                for message in self.pubsub.listen():
                    if not self.running:
                        break
                        
                    if message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])
                            matches = data.get('matches', [])
                            metadata = data.get('metadata', {})
                            
                            # Add subscription metadata
                            metadata.update({
                                'received_timestamp': datetime.now().isoformat(),
                                'source_timestamp': data.get('timestamp'),
                                'source': data.get('source', 'unknown'),
                                'subscription_source': 'redis_pubsub'
                            })
                            
                            logger.info(f"📅 Received {len(matches)} matches via Redis pub/sub")
                            
                            # Log target match if present (for debugging)
                            target_match = next((m for m in matches if m.get('speldatum') == '2025-09-23'), None)
                            if target_match:
                                logger.info(f"🎯 Target match received: {target_match.get('lag1namn')} vs {target_match.get('lag2namn')} on 2025-09-23")
                            
                            # Call handler with matches and metadata
                            handler(matches, metadata)
                            
                        except Exception as e:
                            logger.error(f"❌ Failed to process Redis match update: {e}")
                            
            except Exception as e:
                logger.error(f"❌ Redis subscription failed: {e}")
                if self.running:
                    logger.info("🔄 Attempting to reconnect to Redis in 30 seconds...")
                    time.sleep(30)
                    if self.running:
                        self._connect()
                        if self.is_available():
                            logger.info("🔄 Restarting Redis subscription...")
                            subscription_worker()  # Recursive restart
        
        try:
            # Start subscription in background thread
            self.running = True
            self.subscription_thread = threading.Thread(
                target=subscription_worker, 
                daemon=True, 
                name="redis-match-subscriber"
            )
            self.subscription_thread.start()
            
            # Give it a moment to start
            time.sleep(1)
            
            logger.info("✅ Redis match subscription started in background")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start Redis subscription: {e}")
            return False
    
    def subscribe_to_processing_status(self, handler: Callable[[str, Dict], None]) -> bool:
        """
        Subscribe to processing status updates from Redis.
        
        Args:
            handler: Function to call with (status, details) when status updates received
            
        Returns:
            bool: True if subscription started successfully
        """
        if not self.is_available():
            return False
        
        def status_subscription_worker():
            """Background worker for status subscription."""
            try:
                status_pubsub = self.client.pubsub()
                status_pubsub.subscribe('fogis_status')
                
                logger.info("📊 Calendar service subscribed to Redis processing status")
                
                for message in status_pubsub.listen():
                    if not self.running:
                        break
                        
                    if message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])
                            status = data.get('status', 'unknown')
                            details = data.get('details', {})
                            
                            logger.debug(f"📊 Received processing status: {status}")
                            
                            # Call handler with status and details
                            handler(status, details)
                            
                        except Exception as e:
                            logger.error(f"❌ Failed to process Redis status update: {e}")
                            
            except Exception as e:
                logger.error(f"❌ Redis status subscription failed: {e}")
        
        try:
            # Start status subscription in background thread
            status_thread = threading.Thread(
                target=status_subscription_worker, 
                daemon=True, 
                name="redis-status-subscriber"
            )
            status_thread.start()
            
            logger.info("✅ Redis status subscription started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start Redis status subscription: {e}")
            return False
    
    def stop_subscription(self):
        """Stop Redis subscription."""
        self.running = False
        
        if self.pubsub:
            try:
                self.pubsub.close()
            except:
                pass
        
        logger.info("📡 Redis subscription stopped")

# Global instance for easy access
_redis_client = None

def get_redis_client() -> CalendarServiceRedisPubSub:
    """Get or create global Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = CalendarServiceRedisPubSub()
    return _redis_client

def subscribe_to_match_updates(handler: Callable[[List[Dict], Dict], None]) -> bool:
    """
    Helper function to subscribe to match updates.
    
    Args:
        handler: Function to call with (matches, metadata) when updates received
        
    Returns:
        bool: True if subscription started successfully
    """
    redis_client = get_redis_client()
    return redis_client.subscribe_to_match_updates(handler)

def subscribe_to_processing_status(handler: Callable[[str, Dict], None]) -> bool:
    """
    Helper function to subscribe to processing status.
    
    Args:
        handler: Function to call with (status, details) when status updates received
        
    Returns:
        bool: True if subscription started successfully
    """
    redis_client = get_redis_client()
    return redis_client.subscribe_to_processing_status(handler)

def stop_all_subscriptions():
    """Stop all Redis subscriptions."""
    redis_client = get_redis_client()
    redis_client.stop_subscription()

def test_redis_connection() -> bool:
    """
    Test Redis connection and functionality.
    
    Returns:
        bool: True if Redis is working
    """
    try:
        redis_client = get_redis_client()
        
        if not redis_client.is_available():
            logger.info("⚠️ Redis not available - calendar service will use HTTP endpoints only")
            return False
        
        logger.info("✅ Redis pub/sub test successful")
        return True
            
    except Exception as e:
        logger.error(f"❌ Redis connection test failed: {e}")
        return False

if __name__ == "__main__":
    # Test the module
    logging.basicConfig(level=logging.INFO)
    
    def test_handler(matches, metadata):
        print(f"Received {len(matches)} matches: {metadata}")
    
    def test_status_handler(status, details):
        print(f"Status: {status}, Details: {details}")
    
    # Test connection
    if test_redis_connection():
        # Test subscription
        subscribe_to_match_updates(test_handler)
        subscribe_to_processing_status(test_status_handler)
        
        # Keep running for test
        time.sleep(10)
        
        stop_all_subscriptions()
    else:
        print("Redis not available for testing")
