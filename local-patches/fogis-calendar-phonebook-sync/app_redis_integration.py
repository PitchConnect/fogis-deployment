#!/usr/bin/env python3
"""
Flask App Redis Integration for Calendar Service

This module provides Redis pub/sub integration for the existing Flask-based
calendar service, enabling real-time match updates via Redis subscription.

Author: System Architecture Team
Date: 2025-09-21
Issue: Redis pub/sub integration for calendar service Flask app
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Any

from flask import Flask, jsonify, request

# Import Redis integration
from redis_pubsub_integration import subscribe_to_match_updates, subscribe_to_processing_status, test_redis_connection, stop_all_subscriptions

logger = logging.getLogger(__name__)

class CalendarServiceRedisIntegration:
    """Redis integration for calendar service Flask app."""
    
    def __init__(self, app: Flask):
        """Initialize Redis integration with Flask app."""
        self.app = app
        self.redis_enabled = False
        self.last_sync_time = None
        self.sync_count = 0
        
        # Initialize Redis integration
        self._initialize_redis_integration()
        
        # Add Redis-related endpoints
        self._add_redis_endpoints()
    
    def _initialize_redis_integration(self):
        """Initialize Redis pub/sub integration."""
        try:
            logger.info("🔧 Initializing Redis pub/sub integration for calendar service...")
            
            # Test Redis connection
            redis_available = test_redis_connection()
            
            if redis_available:
                # Start Redis subscriptions
                match_subscription_success = subscribe_to_match_updates(self._handle_match_updates)
                status_subscription_success = subscribe_to_processing_status(self._handle_processing_status)
                
                if match_subscription_success:
                    self.redis_enabled = True
                    logger.info("✅ Redis pub/sub integration enabled for calendar service")
                    logger.info("📡 Subscribed to match updates from match-list-processor")
                else:
                    logger.warning("⚠️ Failed to subscribe to Redis match updates")
                
                if status_subscription_success:
                    logger.info("📊 Subscribed to processing status updates")
                
            else:
                logger.info("⚠️ Redis not available - calendar service will use HTTP endpoints only")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis integration: {e}")
            self.redis_enabled = False
    
    def _handle_match_updates(self, matches: List[Dict], metadata: Dict):
        """
        Handle match updates received via Redis pub/sub.
        
        Args:
            matches: List of match dictionaries
            metadata: Update metadata from match processor
        """
        try:
            logger.info(f"📅 Processing {len(matches)} matches from Redis pub/sub")
            
            # Log metadata for debugging
            logger.debug(f"Update metadata: {metadata}")
            
            # Check if there are actual changes
            has_changes = metadata.get('has_changes', True)  # Default to True for safety
            
            if has_changes:
                logger.info(f"🔄 Changes detected - triggering calendar sync")
                
                # Call existing calendar sync logic
                sync_result = self._sync_matches_to_calendar(matches, metadata)
                
                if sync_result['success']:
                    self.last_sync_time = datetime.now().isoformat()
                    self.sync_count += 1
                    logger.info(f"✅ Calendar sync completed successfully (sync #{self.sync_count})")
                else:
                    logger.error(f"❌ Calendar sync failed: {sync_result.get('error', 'Unknown error')}")
            else:
                logger.info("📋 No changes detected - skipping calendar sync")
                
        except Exception as e:
            logger.error(f"❌ Failed to handle match updates: {e}", exc_info=True)
    
    def _handle_processing_status(self, status: str, details: Dict):
        """
        Handle processing status updates from match processor.
        
        Args:
            status: Processing status (started, completed, failed)
            details: Status details
        """
        try:
            logger.debug(f"📊 Match processor status: {status}")
            
            if status == "failed":
                logger.warning(f"⚠️ Match processor reported failure: {details.get('error', 'Unknown error')}")
            elif status == "completed":
                logger.info("✅ Match processor completed successfully")
                
        except Exception as e:
            logger.error(f"❌ Failed to handle processing status: {e}")
    
    def _sync_matches_to_calendar(self, matches: List[Dict], metadata: Dict) -> Dict[str, Any]:
        """
        Sync matches to calendar using existing calendar sync logic.
        
        This is a placeholder that should call the actual calendar sync implementation.
        
        Args:
            matches: List of match dictionaries
            metadata: Sync metadata
            
        Returns:
            Dict with sync results
        """
        try:
            # TODO: Replace this with actual calendar sync logic
            # This should call the existing calendar sync functionality
            
            logger.info(f"🗓️ Syncing {len(matches)} matches to calendar...")
            
            # Simulate calendar sync for now
            # In real implementation, this would:
            # 1. Process each match
            # 2. Create/update calendar events
            # 3. Handle OAuth authentication
            # 4. Return sync results
            
            # Log target match for debugging
            target_match = next((m for m in matches if m.get('speldatum') == '2025-09-23'), None)
            if target_match:
                logger.info(f"🎯 Processing target match: {target_match.get('lag1namn')} vs {target_match.get('lag2namn')} on 2025-09-23")
            
            # Return success result
            return {
                'success': True,
                'matches_processed': len(matches),
                'events_created': len(matches),  # Placeholder
                'events_updated': 0,
                'timestamp': datetime.now().isoformat(),
                'source': 'redis_pubsub'
            }
            
        except Exception as e:
            logger.error(f"❌ Calendar sync failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'matches_processed': 0,
                'events_created': 0,
                'timestamp': datetime.now().isoformat()
            }
    
    def _add_redis_endpoints(self):
        """Add Redis-related endpoints to Flask app."""
        
        @self.app.route('/redis-status', methods=['GET'])
        def redis_status():
            """Get Redis integration status."""
            return jsonify({
                'redis_enabled': self.redis_enabled,
                'last_sync_time': self.last_sync_time,
                'sync_count': self.sync_count,
                'timestamp': datetime.now().isoformat()
            }), 200
        
        @self.app.route('/redis-test', methods=['POST'])
        def redis_test():
            """Test Redis functionality."""
            try:
                redis_available = test_redis_connection()
                
                return jsonify({
                    'redis_available': redis_available,
                    'redis_enabled': self.redis_enabled,
                    'timestamp': datetime.now().isoformat()
                }), 200
                
            except Exception as e:
                return jsonify({
                    'redis_available': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
    
    def shutdown(self):
        """Shutdown Redis integration."""
        try:
            logger.info("🔄 Shutting down Redis integration...")
            stop_all_subscriptions()
            logger.info("✅ Redis integration shutdown complete")
        except Exception as e:
            logger.error(f"❌ Error during Redis integration shutdown: {e}")

def integrate_redis_with_flask_app(app: Flask) -> CalendarServiceRedisIntegration:
    """
    Integrate Redis pub/sub with existing Flask calendar service app.
    
    Args:
        app: Flask application instance
        
    Returns:
        CalendarServiceRedisIntegration instance
    """
    logger.info("🔗 Integrating Redis pub/sub with calendar service Flask app...")
    
    redis_integration = CalendarServiceRedisIntegration(app)
    
    # Add shutdown handler
    import atexit
    atexit.register(redis_integration.shutdown)
    
    logger.info("✅ Redis integration completed for calendar service")
    
    return redis_integration

# Example usage for testing
if __name__ == "__main__":
    # Create test Flask app
    app = Flask(__name__)
    
    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'healthy'}), 200
    
    # Integrate Redis
    redis_integration = integrate_redis_with_flask_app(app)
    
    # Run test app
    logger.info("🧪 Running test calendar service with Redis integration...")
    app.run(host='0.0.0.0', port=5003, debug=False)
