#!/usr/bin/env python3
"""
Centralized Authentication Service

This service provides centralized OAuth token management for all FOGIS services,
preventing token conflicts and ensuring consistent authentication state.

Author: System Architecture Team
Date: 2025-09-21
Issue: Centralized authentication for FOGIS ecosystem
"""

import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from flask import Flask, jsonify, request

# Import our event system
from fogis_event_system import setup_event_system, EventType

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CentralizedAuthService:
    """Centralized authentication service for FOGIS ecosystem."""
    
    def __init__(self):
        """Initialize centralized auth service."""
        self.tokens = {}
        self.token_locks = {}
        self.refresh_timers = {}
        
        # Initialize event system
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
            self.publisher, _, self.connection_manager = setup_event_system('auth-service', redis_url)
            logger.info("✅ Event system initialized for auth service")
        except Exception as e:
            logger.error(f"❌ Failed to initialize event system: {e}")
            self.publisher = None
        
        # Load existing tokens
        self.load_tokens()
        
        # Start token refresh monitoring
        self.start_token_monitoring()
    
    def load_tokens(self):
        """Load existing tokens from storage."""
        try:
            # Load Google Calendar token
            calendar_token_file = '/app/data/google-calendar/token.json'
            if os.path.exists(calendar_token_file):
                with open(calendar_token_file, 'r') as f:
                    token_data = json.load(f)
                
                self.tokens['google_calendar'] = {
                    'token_data': token_data,
                    'expires_at': self._parse_expiry(token_data.get('expiry')),
                    'service': 'google_calendar',
                    'last_refresh': datetime.now().isoformat()
                }
                
                logger.info("✅ Loaded Google Calendar token")
            
            # Load FOGIS tokens (if any)
            # This can be extended for FOGIS OAuth tokens when available
            
            logger.info(f"Loaded {len(self.tokens)} authentication tokens")
            
        except Exception as e:
            logger.error(f"❌ Failed to load tokens: {e}")
    
    def _parse_expiry(self, expiry_str: Optional[str]) -> Optional[datetime]:
        """Parse token expiry string to datetime."""
        if not expiry_str:
            return None
        
        try:
            # Handle different expiry formats
            if 'T' in expiry_str:
                return datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
            else:
                return datetime.fromisoformat(expiry_str)
        except Exception as e:
            logger.error(f"Failed to parse expiry: {expiry_str}, error: {e}")
            return None
    
    def get_token(self, service: str) -> Optional[Dict[str, Any]]:
        """Get valid token for a service."""
        try:
            if service not in self.tokens:
                logger.warning(f"No token available for service: {service}")
                return None
            
            token_info = self.tokens[service]
            
            # Check if token needs refresh
            if self._token_needs_refresh(token_info):
                logger.info(f"Token for {service} needs refresh")
                if self.refresh_token(service):
                    token_info = self.tokens[service]
                else:
                    logger.error(f"Failed to refresh token for {service}")
                    return None
            
            return token_info['token_data']
            
        except Exception as e:
            logger.error(f"❌ Failed to get token for {service}: {e}")
            return None
    
    def _token_needs_refresh(self, token_info: Dict[str, Any]) -> bool:
        """Check if token needs refresh."""
        expires_at = token_info.get('expires_at')
        if not expires_at:
            return False
        
        # Refresh if expires within 10 minutes
        refresh_threshold = datetime.now() + timedelta(minutes=10)
        return expires_at <= refresh_threshold
    
    def refresh_token(self, service: str) -> bool:
        """Refresh token for a service."""
        try:
            # Acquire lock for this service
            if service not in self.token_locks:
                self.token_locks[service] = threading.Lock()
            
            with self.token_locks[service]:
                logger.info(f"🔄 Refreshing token for {service}")
                
                if service == 'google_calendar':
                    return self._refresh_google_calendar_token()
                else:
                    logger.error(f"Unknown service for token refresh: {service}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Failed to refresh token for {service}: {e}")
            return False
    
    def _refresh_google_calendar_token(self) -> bool:
        """Refresh Google Calendar token."""
        try:
            from google.oauth2.credentials import Credentials
            
            token_info = self.tokens.get('google_calendar')
            if not token_info:
                logger.error("No Google Calendar token to refresh")
                return False
            
            token_data = token_info['token_data']
            
            # Create credentials object
            credentials = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes', [])
            )
            
            # Refresh the token
            credentials.refresh(request=None)
            
            # Update token data
            new_token_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None
            }
            
            # Save to file
            calendar_token_file = '/app/data/google-calendar/token.json'
            with open(calendar_token_file, 'w') as f:
                json.dump(new_token_data, f, indent=2)
            
            # Update in memory
            self.tokens['google_calendar'] = {
                'token_data': new_token_data,
                'expires_at': credentials.expiry,
                'service': 'google_calendar',
                'last_refresh': datetime.now().isoformat()
            }
            
            logger.info("✅ Google Calendar token refreshed successfully")
            
            # Publish token refresh event
            if self.publisher:
                self.publisher.publish_event(
                    EventType.SYSTEM_HEALTH.value,
                    {'service': 'google_calendar', 'action': 'token_refreshed'},
                    {'auth_service': 'centralized', 'expires_at': credentials.expiry.isoformat() if credentials.expiry else None}
                )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to refresh Google Calendar token: {e}")
            return False
    
    def start_token_monitoring(self):
        """Start background token monitoring and refresh."""
        def monitor_tokens():
            while True:
                try:
                    for service, token_info in self.tokens.items():
                        if self._token_needs_refresh(token_info):
                            logger.info(f"Proactively refreshing token for {service}")
                            self.refresh_token(service)
                    
                    # Check every 5 minutes
                    time.sleep(300)
                    
                except Exception as e:
                    logger.error(f"Token monitoring error: {e}")
                    time.sleep(60)  # Wait 1 minute on error
        
        monitor_thread = threading.Thread(target=monitor_tokens, daemon=True)
        monitor_thread.start()
        logger.info("✅ Token monitoring started")
    
    def get_status(self) -> Dict[str, Any]:
        """Get authentication service status."""
        status = {
            'service': 'centralized-auth-service',
            'tokens_managed': len(self.tokens),
            'services': {},
            'timestamp': datetime.now().isoformat()
        }
        
        for service, token_info in self.tokens.items():
            expires_at = token_info.get('expires_at')
            status['services'][service] = {
                'has_token': True,
                'expires_at': expires_at.isoformat() if expires_at else None,
                'expires_in_hours': (expires_at - datetime.now()).total_seconds() / 3600 if expires_at else None,
                'last_refresh': token_info.get('last_refresh'),
                'needs_refresh': self._token_needs_refresh(token_info)
            }
        
        return status

# Flask app for centralized auth service
app = Flask(__name__)
auth_service = CentralizedAuthService()

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'centralized-auth-service',
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/auth/status', methods=['GET'])
def auth_status():
    """Get authentication status."""
    return jsonify(auth_service.get_status()), 200

@app.route('/auth/token/<service>', methods=['GET'])
def get_token(service: str):
    """Get token for a service."""
    token = auth_service.get_token(service)
    
    if token:
        return jsonify({
            'status': 'success',
            'service': service,
            'token': token,
            'timestamp': datetime.now().isoformat()
        }), 200
    else:
        return jsonify({
            'status': 'error',
            'service': service,
            'message': 'Token not available or refresh failed',
            'timestamp': datetime.now().isoformat()
        }), 404

@app.route('/auth/refresh/<service>', methods=['POST'])
def refresh_token_endpoint(service: str):
    """Manually refresh token for a service."""
    success = auth_service.refresh_token(service)
    
    if success:
        return jsonify({
            'status': 'success',
            'service': service,
            'message': 'Token refreshed successfully',
            'timestamp': datetime.now().isoformat()
        }), 200
    else:
        return jsonify({
            'status': 'error',
            'service': service,
            'message': 'Token refresh failed',
            'timestamp': datetime.now().isoformat()
        }), 500

def main():
    """Main function for centralized auth service."""
    logger.info("🚀 Starting Centralized Authentication Service")
    
    # Start Flask app
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5004))
    
    logger.info(f"Centralized Auth Service starting on {host}:{port}")
    logger.info("Available endpoints:")
    logger.info("  GET /health - Health check")
    logger.info("  GET /auth/status - Authentication status")
    logger.info("  GET /auth/token/<service> - Get token for service")
    logger.info("  POST /auth/refresh/<service> - Refresh token for service")
    
    app.run(host=host, port=port, debug=False)

if __name__ == "__main__":
    main()
