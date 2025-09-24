"""
Emergency Fix: Direct Data Feeding Endpoint for Calendar Service

This module adds a new endpoint that accepts match data directly without requiring
FOGIS authentication, resolving the OAuth authentication failures blocking calendar sync.

Author: System Architecture Team
Date: 2025-09-19
Issue: #100 - OAuth authentication failures in calendar service
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import request, jsonify

logger = logging.getLogger(__name__)

class EmergencyDataProcessor:
    """
    Processes match data received directly from match-list-processor
    without requiring FOGIS authentication.
    """
    
    def __init__(self, calendar_sync_handler):
        """
        Initialize with existing calendar sync handler.
        
        Args:
            calendar_sync_handler: Existing calendar synchronization logic
        """
        self.calendar_sync_handler = calendar_sync_handler
        
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
                logger.error(f"Invalid match data type: {type(match)}")
                return False
                
            for field in required_fields:
                if field not in match:
                    logger.error(f"Missing required field '{field}' in match: {match.get('matchid', 'unknown')}")
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
            logger.info(f"Processing emergency sync for {len(match_data)} matches")
            
            # Validate data
            if not self.validate_match_data(match_data):
                raise ValueError("Invalid match data structure")
            
            # Filter for relevant matches (referee assignments)
            relevant_matches = self.filter_referee_matches(match_data)
            logger.info(f"Found {len(relevant_matches)} matches with referee assignments")
            
            # Process matches for calendar sync
            sync_results = self.calendar_sync_handler.sync_matches_to_calendar(relevant_matches)
            
            # Log success
            logger.info(f"Emergency sync completed: {sync_results.get('events_created', 0)} events created")
            
            return {
                'status': 'success',
                'matches_received': len(match_data),
                'matches_processed': len(relevant_matches),
                'events_created': sync_results.get('events_created', 0),
                'events_updated': sync_results.get('events_updated', 0),
                'timestamp': datetime.now().isoformat(),
                'source': 'emergency_data_feed',
                'metadata': metadata or {}
            }
            
        except Exception as e:
            logger.error(f"Emergency sync failed: {e}", exc_info=True)
            raise
    
    def filter_referee_matches(self, matches: List[Dict]) -> List[Dict]:
        """
        Filter matches to only include those with referee assignments.
        
        Args:
            matches: List of all matches
            
        Returns:
            List of matches with referee assignments
        """
        # Get user referee number from config
        user_referee_number = getattr(self.calendar_sync_handler, 'user_referee_number', None)
        
        if not user_referee_number:
            logger.warning("No user referee number configured, returning all matches")
            return matches
        
        relevant_matches = []
        for match in matches:
            # Check if user is assigned as referee
            referee_assignments = match.get('referee_assignments', [])
            
            if any(str(assignment.get('referee_id')) == str(user_referee_number) 
                   for assignment in referee_assignments):
                relevant_matches.append(match)
                logger.debug(f"Match {match.get('matchid')} includes user referee assignment")
        
        return relevant_matches


def add_emergency_endpoint(app, calendar_sync_handler):
    """
    Add emergency data feeding endpoint to Flask app.
    
    Args:
        app: Flask application instance
        calendar_sync_handler: Existing calendar sync handler
    """
    
    emergency_processor = EmergencyDataProcessor(calendar_sync_handler)
    
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
                    "anlaggningnamn": "Åbyvallen 1 Konstgräs",
                    "referee_assignments": [...]
                }
            ],
            "timestamp": "2025-09-19T13:30:00Z",
            "source": "match-list-processor"
        }
        
        Returns:
            JSON response with sync results
        """
        try:
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
            
            logger.info(f"Emergency sync request received: {len(matches)} matches from {metadata['source']}")
            
            # Process the sync
            result = emergency_processor.process_emergency_sync(matches, metadata)
            
            # Log the specific match we're looking for
            target_match = next((m for m in matches if m.get('speldatum') == '2025-09-23'), None)
            if target_match:
                logger.info(f"Target match found: {target_match.get('lag1namn')} vs {target_match.get('lag2namn')} on 2025-09-23")
            
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
                'version': '1.0'
            }), 200
            
        except Exception as e:
            logger.error(f"Emergency status check failed: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500


# Integration example for existing calendar service
def integrate_emergency_fix(app, existing_calendar_handler):
    """
    Integrate emergency fix into existing calendar service.
    
    Args:
        app: Flask application
        existing_calendar_handler: Your existing calendar sync handler
    """
    
    # Add emergency endpoints
    add_emergency_endpoint(app, existing_calendar_handler)
    
    # Update health check to include emergency capability
    @app.route('/health')
    def enhanced_health_check():
        """Enhanced health check including emergency capabilities."""
        try:
            # Get existing health data
            health_data = existing_calendar_handler.get_health_status()
            
            # Add emergency capability info
            health_data['emergency_data_feed'] = {
                'available': True,
                'endpoint': '/sync-with-data',
                'bypasses_fogis_auth': True
            }
            
            return jsonify(health_data), 200
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'emergency_data_feed': {'available': False, 'error': str(e)}
            }), 500
    
    logger.info("Emergency fix integrated successfully")
    logger.info("Calendar service can now receive match data directly via /sync-with-data")
