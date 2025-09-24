#!/usr/bin/env python3
"""
Emergency Calendar Service - Simple Implementation

This is a standalone Flask app that provides the emergency data feeding endpoint
to bypass FOGIS OAuth authentication failures. It runs on a different port
and can be used immediately while the main service is being fixed.

Author: System Architecture Team
Date: 2025-09-19
Issue: #100 - OAuth authentication failures in calendar service
"""

import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime
from typing import Dict, List, Any, Optional

from flask import Flask, jsonify, request

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

class EmergencyCalendarProcessor:
    """
    Processes match data received directly from match-list-processor
    without requiring FOGIS authentication.
    """
    
    def __init__(self):
        """Initialize emergency processor."""
        self.logger = logger
        
    def validate_match_data(self, matches: List[Dict]) -> bool:
        """
        Validate incoming match data structure.
        
        Args:
            matches: List of match dictionaries
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        required_fields = ['matchid', 'speldatum', 'lag1namn', 'lag2namn']
        
        for match in matches:
            if not isinstance(match, dict):
                self.logger.error(f"Invalid match data type: {type(match)}")
                return False
                
            for field in required_fields:
                if field not in match:
                    self.logger.error(f"Missing required field '{field}' in match: {match.get('matchid', 'unknown')}")
                    return False
                    
        return True
    
    def process_emergency_sync(self, match_data: List[Dict], metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process match data for calendar sync without FOGIS authentication.
        
        Args:
            match_data: List of match dictionaries
            metadata: Optional metadata about the sync request
            
        Returns:
            Dict containing sync results
        """
        try:
            self.logger.info(f"Processing emergency sync for {len(match_data)} matches")
            
            # Validate data
            if not self.validate_match_data(match_data):
                raise ValueError("Invalid match data structure")
            
            # Create temporary file with match data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(match_data, f, indent=2)
                temp_file = f.name
            
            self.logger.info(f"Saved {len(match_data)} matches to {temp_file}")
            
            try:
                # Run calendar sync script with environment variable pointing to our data
                env = os.environ.copy()
                env['EMERGENCY_MATCH_DATA_FILE'] = temp_file
                env['EMERGENCY_MODE'] = 'true'
                
                # Run the calendar sync script
                cmd = ['python', '/app/fogis_calendar_sync.py', '--headless']
                
                self.logger.info(f"Running calendar sync: {' '.join(cmd)}")
                process = subprocess.run(
                    cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2 minute timeout
                    cwd='/app'
                )
                
                if process.returncode == 0:
                    self.logger.info("Calendar sync completed successfully")
                    events_created = 1  # Assume success created at least one event
                    
                    # Try to parse output for more details
                    if "events created" in process.stdout.lower():
                        try:
                            # Simple parsing to extract number of events
                            import re
                            match = re.search(r'(\d+)\s+events?\s+created', process.stdout.lower())
                            if match:
                                events_created = int(match.group(1))
                        except:
                            pass
                    
                    return {
                        'status': 'success',
                        'matches_received': len(match_data),
                        'matches_processed': len(match_data),
                        'events_created': events_created,
                        'events_updated': 0,
                        'timestamp': datetime.now().isoformat(),
                        'source': 'emergency_data_feed',
                        'metadata': metadata or {},
                        'sync_output': process.stdout[:500] if process.stdout else ''
                    }
                else:
                    self.logger.error(f"Calendar sync failed: {process.stderr}")
                    raise Exception(f"Calendar sync failed: {process.stderr}")
                    
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            
        except Exception as e:
            self.logger.error(f"Emergency sync failed: {e}", exc_info=True)
            raise

# Global emergency processor instance
emergency_processor = EmergencyCalendarProcessor()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check for emergency service."""
    return jsonify({
        'status': 'healthy',
        'service': 'emergency-calendar-sync',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0',
        'emergency_mode': True,
        'bypasses_fogis_auth': True
    }), 200

@app.route('/sync-with-data', methods=['POST'])
def sync_with_provided_data():
    """
    Emergency endpoint to receive match data directly without FOGIS authentication.
    
    Expected JSON payload:
    {
        "matches": [
            {
                "matchid": 6491192,
                "speldatum": "2025-09-23",
                "avsparkstid": "19:00",
                "lag1namn": "Jitex BK",
                "lag2namn": "Vittsjö GIK",
                "tavlingnamn": "Svenska Cupen 2025/26 omg. 1-3",
                "anlaggningnamn": "Åbyvallen 1 Konstgräs"
            }
        ],
        "timestamp": "2025-09-19T13:30:00Z",
        "source": "match-list-processor"
    }
    
    Returns:
        JSON response with sync results
    """
    try:
        logger.info("🚨 Emergency sync request received")
        
        # Validate request
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'message': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Empty request body'
            }), 400
        
        # Extract match data
        matches = data.get('matches', [])
        if not matches:
            return jsonify({
                'status': 'error',
                'message': 'No matches provided in request'
            }), 400
        
        # Extract metadata
        metadata = {
            'source': data.get('source', 'unknown'),
            'timestamp': data.get('timestamp'),
            'request_id': request.headers.get('X-Request-ID', 'unknown')
        }
        
        logger.info(f"Emergency sync request: {len(matches)} matches from {metadata['source']}")
        
        # Log the specific match we're looking for
        target_match = next((m for m in matches if m.get('speldatum') == '2025-09-23'), None)
        if target_match:
            logger.info(f"🎯 Target match found: {target_match.get('lag1namn')} vs {target_match.get('lag2namn')} on 2025-09-23")
        
        # Process the sync
        result = emergency_processor.process_emergency_sync(matches, metadata)
        
        logger.info(f"✅ Emergency sync completed: {result.get('events_created', 0)} events created")
        
        return jsonify(result), 200
        
    except ValueError as e:
        logger.error(f"Validation error in emergency sync: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Data validation failed: {str(e)}'
        }), 400
        
    except Exception as e:
        logger.error(f"Emergency sync endpoint failed: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }), 500

@app.route('/emergency-status', methods=['GET'])
def emergency_status():
    """
    Check emergency endpoint status and capabilities.
    
    Returns:
        JSON response with endpoint status
    """
    try:
        return jsonify({
            'status': 'available',
            'service': 'emergency-calendar-sync',
            'endpoint': '/sync-with-data',
            'method': 'POST',
            'description': 'Emergency data feeding endpoint for calendar sync',
            'bypasses_fogis_auth': True,
            'timestamp': datetime.now().isoformat(),
            'version': '1.0',
            'port': 9084,
            'note': 'This is a temporary emergency service running on port 9084'
        }), 200
        
    except Exception as e:
        logger.error(f"Emergency status check failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to verify the service is working."""
    return jsonify({
        'status': 'ok',
        'message': 'Emergency calendar service is running',
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            '/health': 'Health check',
            '/sync-with-data': 'Emergency data feeding (POST)',
            '/emergency-status': 'Service status',
            '/test': 'Test endpoint'
        }
    }), 200

if __name__ == "__main__":
    # Use a different port to avoid conflicts
    host = "0.0.0.0"
    port = 9084
    
    logger.info(f"🚨 Starting Emergency Calendar Service on {host}:{port}")
    logger.info("This service provides emergency data feeding to bypass FOGIS OAuth failures")
    logger.info("Available endpoints:")
    logger.info("  POST /sync-with-data - Emergency calendar sync")
    logger.info("  GET /emergency-status - Service status")
    logger.info("  GET /health - Health check")
    logger.info("  GET /test - Test endpoint")
    
    app.run(host=host, port=port, debug=False)
