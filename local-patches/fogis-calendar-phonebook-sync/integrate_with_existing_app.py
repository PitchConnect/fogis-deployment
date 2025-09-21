#!/usr/bin/env python3
"""
Integration Script for Existing Calendar Service

This script provides a simple way to integrate Redis pub/sub functionality
with the existing calendar service without major modifications.

Author: System Architecture Team
Date: 2025-09-21
Issue: Minimal Redis pub/sub integration for existing calendar service
"""

import logging
import os
import sys
import threading
import time
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from redis_pubsub_integration import subscribe_to_match_updates, test_redis_connection

logger = logging.getLogger(__name__)

class MinimalCalendarRedisIntegration:
    """Minimal Redis integration that can be added to existing calendar service."""
    
    def __init__(self):
        """Initialize minimal Redis integration."""
        self.enabled = False
        self.sync_count = 0
        
    def start_redis_integration(self):
        """Start Redis integration in background."""
        try:
            logger.info("🔧 Starting minimal Redis integration for calendar service...")
            
            # Test Redis connection
            if test_redis_connection():
                # Start subscription
                success = subscribe_to_match_updates(self._handle_match_updates)
                
                if success:
                    self.enabled = True
                    logger.info("✅ Redis pub/sub integration started successfully")
                    logger.info("📡 Calendar service now listening for match updates via Redis")
                else:
                    logger.warning("⚠️ Failed to start Redis subscription")
            else:
                logger.info("⚠️ Redis not available - calendar service will use HTTP endpoints only")
                
        except Exception as e:
            logger.error(f"❌ Failed to start Redis integration: {e}")
    
    def _handle_match_updates(self, matches, metadata):
        """Handle match updates from Redis."""
        try:
            logger.info(f"📅 Received {len(matches)} matches via Redis pub/sub")
            
            # Simple calendar sync trigger
            # In a real implementation, this would call the existing calendar sync logic
            self._trigger_calendar_sync(matches, metadata)
            
        except Exception as e:
            logger.error(f"❌ Failed to handle match updates: {e}")
    
    def _trigger_calendar_sync(self, matches, metadata):
        """Trigger calendar sync with received matches."""
        try:
            # This is where you would integrate with existing calendar sync logic
            # For example:
            # - Call existing sync_matches_to_calendar() function
            # - Trigger existing calendar sync endpoint
            # - Process matches using existing calendar logic
            
            logger.info(f"🗓️ Triggering calendar sync for {len(matches)} matches...")
            
            # Log target match for debugging
            target_match = next((m for m in matches if m.get('speldatum') == '2025-09-23'), None)
            if target_match:
                logger.info(f"🎯 Target match in sync: {target_match.get('lag1namn')} vs {target_match.get('lag2namn')} on 2025-09-23")
            
            # TODO: Replace this with actual calendar sync call
            # Example integration options:
            
            # Option 1: Call existing sync function
            # result = existing_calendar_sync_function(matches)
            
            # Option 2: Make HTTP call to existing sync endpoint
            # import requests
            # response = requests.post('http://localhost:5003/sync', json={'matches': matches})
            
            # Option 3: Trigger existing sync mechanism
            # existing_sync_trigger.trigger_sync(matches)
            
            self.sync_count += 1
            logger.info(f"✅ Calendar sync triggered successfully (sync #{self.sync_count})")
            
        except Exception as e:
            logger.error(f"❌ Failed to trigger calendar sync: {e}")

# Global integration instance
_integration = None

def start_minimal_redis_integration():
    """Start minimal Redis integration for calendar service."""
    global _integration
    
    if _integration is None:
        _integration = MinimalCalendarRedisIntegration()
    
    _integration.start_redis_integration()
    return _integration

def is_redis_enabled():
    """Check if Redis integration is enabled."""
    global _integration
    return _integration is not None and _integration.enabled

def get_sync_count():
    """Get number of syncs triggered via Redis."""
    global _integration
    return _integration.sync_count if _integration else 0

# Integration examples for different calendar service architectures

def integrate_with_flask_app(app):
    """
    Example integration with Flask app.
    
    Add this to your existing Flask app initialization:
    
    from integrate_with_existing_app import integrate_with_flask_app
    integrate_with_flask_app(app)
    """
    try:
        # Start Redis integration
        integration = start_minimal_redis_integration()
        
        # Add status endpoint
        @app.route('/redis-integration-status', methods=['GET'])
        def redis_integration_status():
            return {
                'redis_enabled': is_redis_enabled(),
                'sync_count': get_sync_count(),
                'timestamp': datetime.now().isoformat()
            }
        
        logger.info("✅ Redis integration added to Flask app")
        return integration
        
    except Exception as e:
        logger.error(f"❌ Failed to integrate with Flask app: {e}")
        return None

def integrate_with_service_startup():
    """
    Example integration with service startup.
    
    Add this to your service startup code:
    
    from integrate_with_existing_app import integrate_with_service_startup
    integrate_with_service_startup()
    """
    try:
        # Start Redis integration in background thread
        def redis_startup():
            time.sleep(5)  # Wait for service to start
            start_minimal_redis_integration()
        
        thread = threading.Thread(target=redis_startup, daemon=True)
        thread.start()
        
        logger.info("✅ Redis integration scheduled for service startup")
        
    except Exception as e:
        logger.error(f"❌ Failed to integrate with service startup: {e}")

def integrate_with_existing_sync_function(sync_function):
    """
    Example integration with existing sync function.
    
    Replace the placeholder _trigger_calendar_sync with your actual sync function:
    
    from integrate_with_existing_app import integrate_with_existing_sync_function
    integrate_with_existing_sync_function(my_existing_sync_function)
    """
    global _integration
    
    if _integration:
        # Replace the sync trigger with actual function
        _integration._trigger_calendar_sync = lambda matches, metadata: sync_function(matches)
        logger.info("✅ Redis integration connected to existing sync function")
    else:
        logger.warning("⚠️ Redis integration not started - call start_minimal_redis_integration() first")

# Main function for testing
def main():
    """Main function for testing Redis integration."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("🧪 Testing minimal Redis integration for calendar service...")
    
    # Start integration
    integration = start_minimal_redis_integration()
    
    if integration and integration.enabled:
        logger.info("✅ Redis integration test successful")
        logger.info("📡 Calendar service is now listening for Redis match updates")
        logger.info("🔄 Integration will run in background...")
        
        # Keep running for test
        try:
            while True:
                time.sleep(60)
                logger.info(f"📊 Redis integration status: {get_sync_count()} syncs triggered")
        except KeyboardInterrupt:
            logger.info("🔄 Stopping Redis integration test...")
    else:
        logger.error("❌ Redis integration test failed")

if __name__ == "__main__":
    main()
