#!/usr/bin/env python3
"""
Flask Integration for Calendar Service Redis

This module provides Flask application integration for Redis subscription functionality
in the FOGIS calendar service, enabling seamless integration with existing Flask endpoints.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Flask integration for calendar service Redis subscription
"""

import logging
import os
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from flask import Flask, jsonify, request

from .redis_service import CalendarServiceRedisService
from .config import get_redis_subscription_config

logger = logging.getLogger(__name__)

class CalendarRedisFlaskIntegration:
    """Flask integration for calendar Redis subscription service."""
    
    def __init__(self, app: Flask = None, calendar_sync_callback: Callable[[List[Dict]], bool] = None):
        """
        Initialize Flask integration for calendar Redis service.
        
        Args:
            app: Flask application instance (optional)
            calendar_sync_callback: Function to call for calendar synchronization
        """
        self.app = app
        self.redis_service: Optional[CalendarServiceRedisService] = None
        self.calendar_sync_callback = calendar_sync_callback
        
        if app is not None:
            self.init_app(app, calendar_sync_callback)
    
    def init_app(self, app: Flask, calendar_sync_callback: Callable[[List[Dict]], bool] = None) -> None:
        """
        Initialize Flask application with Redis integration.
        
        Args:
            app: Flask application instance
            calendar_sync_callback: Function to call for calendar synchronization
        """
        self.app = app
        self.calendar_sync_callback = calendar_sync_callback or self.calendar_sync_callback
        
        # Create Redis service
        self.redis_service = CalendarServiceRedisService(
            calendar_sync_callback=self.calendar_sync_callback
        )
        
        # Add Redis service to Flask app
        app.redis_service = self.redis_service
        
        # Register Redis endpoints
        self._register_redis_endpoints()
        
        # Start Redis subscription if enabled
        if self.redis_service.enabled:
            self.redis_service.start_redis_subscription()
            logger.info("✅ Redis subscription started with Flask application")
        
        # Register shutdown handler
        @app.teardown_appcontext
        def close_redis_service(error):
            if hasattr(app, 'redis_service') and app.redis_service:
                app.redis_service.close()
        
        logger.info("✅ Calendar Redis Flask integration initialized")
    
    def _register_redis_endpoints(self) -> None:
        """Register Redis-related Flask endpoints."""
        
        @self.app.route('/redis-status', methods=['GET'])
        def redis_status():
            """Get Redis integration status."""
            try:
                status = self.redis_service.get_redis_status()
                return jsonify({
                    "success": True,
                    "timestamp": datetime.now().isoformat(),
                    "redis_status": status
                }), 200
                
            except Exception as e:
                logger.error(f"❌ Error getting Redis status: {e}")
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/redis-stats', methods=['GET'])
        def redis_stats():
            """Get Redis subscription statistics."""
            try:
                stats = self.redis_service.get_subscription_statistics()
                return jsonify({
                    "success": True,
                    "timestamp": datetime.now().isoformat(),
                    "statistics": stats
                }), 200
                
            except Exception as e:
                logger.error(f"❌ Error getting Redis statistics: {e}")
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/redis-test', methods=['POST'])
        def redis_test():
            """Test Redis integration functionality."""
            try:
                test_results = self.redis_service.test_redis_integration()
                
                return jsonify({
                    "success": True,
                    "timestamp": datetime.now().isoformat(),
                    "test_results": test_results
                }), 200
                
            except Exception as e:
                logger.error(f"❌ Error testing Redis integration: {e}")
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/redis-restart', methods=['POST'])
        def redis_restart():
            """Restart Redis subscription."""
            try:
                success = self.redis_service.restart_subscription()
                
                return jsonify({
                    "success": success,
                    "timestamp": datetime.now().isoformat(),
                    "message": "Redis subscription restarted" if success else "Failed to restart Redis subscription"
                }), 200 if success else 500
                
            except Exception as e:
                logger.error(f"❌ Error restarting Redis subscription: {e}")
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/manual-sync', methods=['POST'])
        def manual_sync():
            """Manual calendar sync endpoint (fallback for HTTP)."""
            try:
                data = request.get_json()
                
                if not data or 'matches' not in data:
                    return jsonify({
                        "success": False,
                        "error": "Missing 'matches' in request data",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                matches = data['matches']
                
                logger.info(f"📅 Manual sync request received for {len(matches)} matches")
                
                # Process manual sync
                success = self.redis_service.handle_manual_sync_request(matches)
                
                return jsonify({
                    "success": success,
                    "timestamp": datetime.now().isoformat(),
                    "matches_processed": len(matches),
                    "message": "Manual sync completed" if success else "Manual sync failed"
                }), 200 if success else 500
                
            except Exception as e:
                logger.error(f"❌ Error in manual sync: {e}")
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/redis-config', methods=['GET'])
        def redis_config():
            """Get Redis configuration information."""
            try:
                config = get_redis_subscription_config()
                config_manager = config.__class__(config)
                status_summary = config_manager.get_status_summary()
                
                return jsonify({
                    "success": True,
                    "timestamp": datetime.now().isoformat(),
                    "configuration": status_summary
                }), 200
                
            except Exception as e:
                logger.error(f"❌ Error getting Redis configuration: {e}")
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        logger.info("📡 Redis endpoints registered with Flask application")
    
    def set_calendar_sync_callback(self, callback: Callable[[List[Dict]], bool]) -> None:
        """
        Set or update the calendar synchronization callback.
        
        Args:
            callback: Function to call for calendar synchronization
        """
        self.calendar_sync_callback = callback
        
        if self.redis_service:
            self.redis_service.set_calendar_sync_callback(callback)
            logger.info("✅ Calendar sync callback updated in Flask integration")
    
    def get_redis_service(self) -> Optional[CalendarServiceRedisService]:
        """
        Get the Redis service instance.
        
        Returns:
            Optional[CalendarServiceRedisService]: Redis service instance
        """
        return self.redis_service

# Convenience functions for external use
def create_calendar_redis_flask_integration(app: Flask = None, 
                                          calendar_sync_callback: Callable[[List[Dict]], bool] = None) -> CalendarRedisFlaskIntegration:
    """
    Create Flask integration for calendar Redis service.
    
    Args:
        app: Flask application instance (optional)
        calendar_sync_callback: Function to call for calendar synchronization
        
    Returns:
        CalendarRedisFlaskIntegration: Configured Flask integration
    """
    return CalendarRedisFlaskIntegration(app, calendar_sync_callback)

def integrate_redis_with_existing_flask_app(app: Flask, 
                                          calendar_sync_callback: Callable[[List[Dict]], bool] = None) -> CalendarRedisFlaskIntegration:
    """
    Integrate Redis subscription with existing Flask application.
    
    Args:
        app: Existing Flask application instance
        calendar_sync_callback: Function to call for calendar synchronization
        
    Returns:
        CalendarRedisFlaskIntegration: Configured Flask integration
    """
    integration = CalendarRedisFlaskIntegration()
    integration.init_app(app, calendar_sync_callback)
    return integration

def add_redis_to_calendar_app(app: Flask, calendar_sync_function: Callable[[List[Dict]], bool]) -> None:
    """
    Add Redis integration to existing calendar Flask application.
    
    Args:
        app: Flask application instance
        calendar_sync_function: Existing calendar synchronization function
    """
    logger.info("🔗 Adding Redis integration to existing calendar Flask app...")
    
    # Create integration
    integration = integrate_redis_with_existing_flask_app(app, calendar_sync_function)
    
    # Add integration to app for reference
    app.redis_integration = integration
    
    logger.info("✅ Redis integration added to calendar Flask application")
    logger.info("📡 Available Redis endpoints:")
    logger.info("   GET  /redis-status  - Redis integration status")
    logger.info("   GET  /redis-stats   - Redis subscription statistics")
    logger.info("   POST /redis-test    - Test Redis integration")
    logger.info("   POST /redis-restart - Restart Redis subscription")
    logger.info("   POST /manual-sync   - Manual calendar sync (fallback)")
    logger.info("   GET  /redis-config  - Redis configuration")

# Example integration code
INTEGRATION_EXAMPLE = '''
# Example of how to integrate Redis into existing calendar Flask application

from flask import Flask
from redis_integration.flask_integration import add_redis_to_calendar_app

app = Flask(__name__)

# Your existing calendar sync function
def existing_calendar_sync_function(matches):
    """Your existing calendar synchronization logic."""
    # Process matches and sync with Google Calendar
    # Return True if successful, False otherwise
    return True

# Add Redis integration to your Flask app
add_redis_to_calendar_app(app, existing_calendar_sync_function)

# Your existing routes continue to work
@app.route('/sync', methods=['POST'])
def sync():
    # Your existing sync endpoint
    pass

# New Redis endpoints are automatically available:
# GET  /redis-status  - Check Redis integration status
# POST /manual-sync   - Manual sync endpoint (fallback for HTTP)
# etc.

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)
'''

if __name__ == "__main__":
    # Test Flask integration
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("🧪 Testing Flask integration...")
    
    # Create test Flask app
    app = Flask(__name__)
    
    # Test calendar sync function
    def test_calendar_sync(matches):
        logger.info(f"📅 Test calendar sync called with {len(matches)} matches")
        return True
    
    # Create integration
    integration = create_calendar_redis_flask_integration(app, test_calendar_sync)
    
    # Test endpoints
    with app.test_client() as client:
        # Test Redis status endpoint
        response = client.get('/redis-status')
        if response.status_code == 200:
            logger.info("✅ Redis status endpoint test successful")
        else:
            logger.warning("⚠️ Redis status endpoint test failed")
        
        # Test Redis config endpoint
        response = client.get('/redis-config')
        if response.status_code == 200:
            logger.info("✅ Redis config endpoint test successful")
        else:
            logger.warning("⚠️ Redis config endpoint test failed")
    
    logger.info("✅ Flask integration test completed")
