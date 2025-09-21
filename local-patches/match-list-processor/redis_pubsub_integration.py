#!/usr/bin/env python3
"""
Redis Pub/Sub Integration for Match List Processor

This module provides minimal Redis pub/sub functionality for the match-list-processor
to publish match updates to downstream services like the calendar service.

Author: System Architecture Team
Date: 2025-09-21
Issue: Redis pub/sub integration for match-list-processor
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class MatchProcessorRedisPubSub:
    """Minimal Redis pub/sub client for match-list-processor."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis pub/sub client."""
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://redis:6379')
        self.client = None
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
            logger.info(f"✅ Match processor connected to Redis: {self.redis_url}")
        except ImportError:
            logger.warning("⚠️ Redis package not installed - pub/sub disabled, using HTTP fallback")
            self.client = None
            self.enabled = False
        except Exception as e:
            logger.warning(f"⚠️ Failed to connect to Redis: {e} - using HTTP fallback")
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
    
    def publish_match_updates(self, all_matches: List[Dict], changes: Dict[str, Any]) -> bool:
        """
        Publish match updates to Redis.
        
        Args:
            all_matches: Complete list of current matches
            changes: Change detection results from MatchComparator
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        if not self.is_available():
            logger.debug("Redis not available for publishing match updates")
            return False
        
        try:
            # Prepare message with all current matches and change metadata
            message = {
                'matches': all_matches,
                'timestamp': datetime.now().isoformat(),
                'source': 'match-list-processor',
                'metadata': {
                    'total_matches': len(all_matches),
                    'has_changes': changes.get('has_changes', False),
                    'new_matches_count': len(changes.get('new_matches', {})),
                    'updated_matches_count': len(changes.get('updated_matches', {})),
                    'processing_timestamp': datetime.now().isoformat()
                }
            }
            
            # Publish to main channel
            subscribers = self.client.publish('fogis_matches', json.dumps(message))
            
            logger.info(f"📡 Published match updates to Redis: {len(all_matches)} matches ({subscribers} subscribers)")
            
            # Log specific changes for debugging
            if changes.get('has_changes'):
                logger.info(f"   Changes: {len(changes.get('new_matches', {}))} new, {len(changes.get('updated_matches', {}))} updated")
            
            # Log target match if present (for debugging the 2025-09-23 issue)
            target_match = next((m for m in all_matches if m.get('speldatum') == '2025-09-23'), None)
            if target_match:
                logger.info(f"🎯 Target match included in Redis publish: {target_match.get('lag1namn')} vs {target_match.get('lag2namn')}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to publish match updates to Redis: {e}")
            return False
    
    def publish_processing_status(self, status: str, details: Dict[str, Any]) -> bool:
        """
        Publish processing status updates.
        
        Args:
            status: Processing status (started, completed, failed)
            details: Additional status details
            
        Returns:
            bool: True if published successfully
        """
        if not self.is_available():
            return False
        
        try:
            message = {
                'type': 'processing_status',
                'status': status,
                'timestamp': datetime.now().isoformat(),
                'source': 'match-list-processor',
                'details': details
            }
            
            subscribers = self.client.publish('fogis_status', json.dumps(message))
            logger.debug(f"📡 Published processing status: {status} ({subscribers} subscribers)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to publish processing status: {e}")
            return False

# Global instance for easy access
_redis_client = None

def get_redis_client() -> MatchProcessorRedisPubSub:
    """Get or create global Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = MatchProcessorRedisPubSub()
    return _redis_client

def publish_match_updates(all_matches: List[Dict], changes: Dict[str, Any]) -> bool:
    """
    Helper function to publish match updates.
    
    Args:
        all_matches: Complete list of current matches
        changes: Change detection results
        
    Returns:
        bool: True if published successfully
    """
    redis_client = get_redis_client()
    return redis_client.publish_match_updates(all_matches, changes)

def publish_processing_status(status: str, **details) -> bool:
    """
    Helper function to publish processing status.
    
    Args:
        status: Processing status
        **details: Additional status details
        
    Returns:
        bool: True if published successfully
    """
    redis_client = get_redis_client()
    return redis_client.publish_processing_status(status, details)

def test_redis_connection() -> bool:
    """
    Test Redis connection and functionality.
    
    Returns:
        bool: True if Redis is working
    """
    try:
        redis_client = get_redis_client()
        
        if not redis_client.is_available():
            logger.info("⚠️ Redis not available - match processor will use HTTP fallback")
            return False
        
        # Test publishing
        test_matches = [
            {
                'match_id': 'test_123',
                'speldatum': '2025-09-21',
                'lag1namn': 'Test Team 1',
                'lag2namn': 'Test Team 2'
            }
        ]
        
        test_changes = {
            'has_changes': True,
            'new_matches': {'test_123': test_matches[0]},
            'updated_matches': {}
        }
        
        if redis_client.publish_match_updates(test_matches, test_changes):
            logger.info("✅ Redis pub/sub test successful")
            return True
        else:
            logger.warning("⚠️ Redis pub/sub test failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Redis connection test failed: {e}")
        return False

if __name__ == "__main__":
    # Test the module
    logging.basicConfig(level=logging.INFO)
    test_redis_connection()
