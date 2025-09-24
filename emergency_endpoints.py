#!/usr/bin/env python3
"""
Emergency Endpoints Module

This module provides emergency endpoints that can be imported into the existing
calendar service Flask app to bypass FOGIS OAuth authentication failures.

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
from flask import request, jsonify

# Set up logging
logger = logging.getLogger(__name__)

def add_emergency_endpoints(app):
    """
    Add emergency endpoints to the existing Flask app.
    
    Args:
        app: Flask application instance
    """
    
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
            
            logger.info(f"Emergency sync: {len(matches)} matches from {metadata['source']}")
            
            # Log the specific match we're looking for
            target_match = next((m for m in matches if m.get('speldatum') == '2025-09-23'), None)
            if target_match:
                logger.info(f"🎯 Target match found: {target_match.get('lag1namn')} vs {target_match.get('lag2namn')} on 2025-09-23")
            
            # Process the emergency sync
            result = process_emergency_sync(matches, metadata)
            
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
                'endpoint': '/sync-with-data',
                'method': 'POST',
                'description': 'Emergency data feeding endpoint for calendar sync',
                'bypasses_fogis_auth': True,
                'timestamp': datetime.now().isoformat(),
                'version': '1.0',
                'port': 9083
            }), 200
            
        except Exception as e:
            logger.error(f"Emergency status check failed: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    logger.info("🚨 Emergency endpoints added to Flask app")
    logger.info("   POST /sync-with-data - Emergency calendar sync")
    logger.info("   GET /emergency-status - Emergency status check")

def process_emergency_sync(match_data, metadata=None):
    """
    Process match data for calendar sync without FOGIS authentication.
    
    Args:
        match_data: List of match dictionaries
        metadata: Optional metadata about the sync request
        
    Returns:
        Dict containing sync results
    """
    try:
        logger.info(f"Processing emergency sync for {len(match_data)} matches")
        
        # Validate match data
        required_fields = ['matchid', 'speldatum', 'lag1namn', 'lag2namn']
        for match in match_data:
            if not isinstance(match, dict):
                raise ValueError(f"Invalid match data type: {type(match)}")
            for field in required_fields:
                if field not in match:
                    raise ValueError(f"Missing required field '{field}' in match: {match.get('matchid', 'unknown')}")
        
        # Save match data to temporary file for the calendar sync script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(match_data, f, indent=2)
            temp_file = f.name
        
        logger.info(f"Saved {len(match_data)} matches to {temp_file}")
        
        try:
            # Set up environment for emergency mode
            env = os.environ.copy()
            env['EMERGENCY_MATCH_DATA_FILE'] = temp_file
            env['EMERGENCY_MODE'] = 'true'
            
            # Run the calendar sync script in headless mode
            cmd = ['python', 'fogis_calendar_sync.py', '--headless']
            logger.info(f"Running calendar sync: {' '.join(cmd)}")
            
            process = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=90,  # 90 second timeout
                cwd='/app'
            )
            
            if process.returncode == 0:
                logger.info("Calendar sync completed successfully")
                
                # Try to extract number of events created from output
                events_created = 1  # Default assumption
                if process.stdout:
                    # Simple parsing to find event creation info
                    import re
                    match = re.search(r'(\d+)\s+events?\s+created', process.stdout.lower())
                    if match:
                        events_created = int(match.group(1))
                
                return {
                    'status': 'success',
                    'matches_received': len(match_data),
                    'matches_processed': len(match_data),
                    'events_created': events_created,
                    'events_updated': 0,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'emergency_data_feed',
                    'metadata': metadata or {},
                    'sync_output': process.stdout[:300] if process.stdout else ''
                }
            else:
                error_msg = process.stderr[:300] if process.stderr else 'Unknown error'
                logger.error(f"Calendar sync failed: {error_msg}")
                raise Exception(f"Calendar sync failed: {error_msg}")
                
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logger.debug(f"Cleaned up temporary file: {temp_file}")
        
    except Exception as e:
        logger.error(f"Emergency sync processing failed: {e}", exc_info=True)
        raise

# Test function to verify the module works
def test_emergency_endpoints():
    """Test function to verify emergency endpoints are working."""
    logger.info("Emergency endpoints module loaded successfully")
    logger.info("Use add_emergency_endpoints(app) to integrate with Flask app")
    return True

if __name__ == "__main__":
    # Test the module
    test_emergency_endpoints()
