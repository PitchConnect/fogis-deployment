#!/usr/bin/env python3
"""
Calendar Service Event Integration

This module integrates event subscription into the calendar service,
enabling event-driven calendar synchronization.

Author: System Architecture Team
Date: 2025-09-21
Issue: Event-driven architecture for calendar service
"""

import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional

# Import our event system
from fogis_event_system import setup_event_system, FOGISEvent

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EventDrivenCalendarService:
    """Calendar service with event-driven architecture."""
    
    def __init__(self, enable_events: bool = True, enable_emergency_endpoint: bool = True):
        """Initialize event-driven calendar service."""
        self.enable_events = enable_events and os.getenv('EVENT_SUBSCRIPTION_ENABLED', 'false').lower() == 'true'
        self.enable_emergency_endpoint = enable_emergency_endpoint
        
        # Initialize event system if enabled
        if self.enable_events:
            try:
                redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
                _, self.subscriber, self.connection_manager = setup_event_system('calendar-service', redis_url)
                
                # Register event handlers
                self.subscriber.register_match_handler(self.handle_match_events)
                
                logger.info("✅ Event subscription system initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize event system: {e}")
                self.enable_events = False
                self.subscriber = None
        else:
            self.subscriber = None
            logger.info("Event subscription disabled")
        
        # Calendar service state
        self.calendar_service = None
        self.last_sync_time = None
        
    def initialize_google_calendar(self):
        """Initialize Google Calendar service."""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            # Load token from file
            token_file = '/app/data/google-calendar/token.json'
            
            if not os.path.exists(token_file):
                raise FileNotFoundError(f"Google Calendar token file not found: {token_file}")
            
            with open(token_file, 'r') as f:
                token_data = json.load(f)
            
            # Create credentials
            credentials = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes', [])
            )
            
            # Build service
            self.calendar_service = build('calendar', 'v3', credentials=credentials)
            logger.info("✅ Google Calendar service initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Calendar service: {e}")
            return False
    
    def handle_match_events(self, matches: List[Dict], metadata: Dict):
        """Handle incoming match events from event system."""
        try:
            logger.info(f"📅 Received match events: {len(matches)} matches")
            logger.info(f"Event metadata: {metadata}")
            
            # Log target match if present
            target_match = next((m for m in matches if m.get('speldatum') == '2025-09-23'), None)
            if target_match:
                logger.info(f"🎯 Target match in event: {target_match.get('lag1naam')} vs {target_match.get('lag2namn')}")
            
            # Process matches for calendar sync
            result = self.sync_matches_to_calendar(matches, metadata)
            
            if result['status'] == 'success':
                logger.info(f"✅ Event-driven calendar sync completed: {result['events_created']} events created")
            else:
                logger.error(f"❌ Event-driven calendar sync failed: {result}")
            
        except Exception as e:
            logger.error(f"❌ Error handling match events: {e}", exc_info=True)
    
    def sync_matches_to_calendar(self, matches: List[Dict], metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Sync matches to Google Calendar."""
        try:
            logger.info(f"📅 Syncing {len(matches)} matches to Google Calendar...")
            
            # Initialize Google Calendar if needed
            if not self.calendar_service:
                if not self.initialize_google_calendar():
                    raise Exception("Failed to initialize Google Calendar service")
            
            # Process each match
            events_created = 0
            events_failed = 0
            
            for match in matches:
                try:
                    if self.create_calendar_event(match):
                        events_created += 1
                    else:
                        events_failed += 1
                except Exception as e:
                    logger.error(f"Failed to process match {match.get('matchid', 'unknown')}: {e}")
                    events_failed += 1
            
            # Update sync time
            self.last_sync_time = datetime.now().isoformat()
            
            result = {
                'status': 'success' if events_created > 0 else 'failed',
                'matches_received': len(matches),
                'matches_processed': len(matches),
                'events_created': events_created,
                'events_failed': events_failed,
                'timestamp': self.last_sync_time,
                'source': 'event_driven_sync',
                'metadata': metadata or {}
            }
            
            logger.info(f"Calendar sync completed: {events_created} created, {events_failed} failed")
            return result
            
        except Exception as e:
            logger.error(f"❌ Calendar sync failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'matches_received': len(matches),
                'matches_processed': 0,
                'events_created': 0,
                'events_failed': len(matches),
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def create_calendar_event(self, match: Dict) -> bool:
        """Create a calendar event for a match."""
        try:
            # Extract match details
            match_id = match.get('matchid')
            match_date = match.get('speldatum')
            match_time = match.get('avsparkstid', '00:00')
            team1 = match.get('lag1namn')
            team2 = match.get('lag2namn')
            venue = match.get('anlaggningnamn', 'Unknown venue')
            competition = match.get('tavlingnamn', 'Unknown competition')
            
            logger.debug(f"Creating event: {team1} vs {team2} on {match_date} at {match_time}")
            
            # Parse datetime
            datetime_str = f"{match_date} {match_time}"
            match_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
            
            # Add timezone offset for Swedish time (UTC+2 for September)
            swedish_offset = timezone(timedelta(hours=2))
            match_datetime = match_datetime.replace(tzinfo=swedish_offset)
            
            # Event duration (2 hours)
            end_datetime = match_datetime + timedelta(hours=2)
            
            # Create event
            event = {
                'summary': f"{team1} vs {team2}",
                'description': f"""Match Details:
• Competition: {competition}
• Venue: {venue}
• Date: {match_date}
• Time: {match_time}
• Match ID: {match_id}

📡 Added via Event-Driven Calendar Sync
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}""",
                'start': {
                    'dateTime': match_datetime.isoformat(),
                    'timeZone': 'Europe/Stockholm',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'Europe/Stockholm',
                },
                'location': venue,
            }
            
            # Insert event
            calendar_id = 'primary'
            created_event = self.calendar_service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()
            
            event_id = created_event.get('id')
            logger.debug(f"✅ Created calendar event: {event_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create event for match {match.get('matchid', 'unknown')}: {e}")
            return False
    
    def start_event_subscription(self):
        """Start event subscription for calendar service."""
        if not self.enable_events or not self.subscriber:
            logger.info("Event subscription disabled or not available")
            return False
        
        try:
            logger.info("📡 Starting event subscription for calendar service...")
            
            # Subscribe to match events
            channels = ['fogis.matches.all']
            self.subscriber.start_subscription(channels)
            
            logger.info("✅ Event subscription started successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start event subscription: {e}")
            return False
    
    def stop_event_subscription(self):
        """Stop event subscription."""
        if self.subscriber:
            self.subscriber.stop()
            logger.info("Event subscription stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get calendar service status."""
        return {
            'service': 'event-driven-calendar-service',
            'event_subscription_enabled': self.enable_events,
            'emergency_endpoint_enabled': self.enable_emergency_endpoint,
            'calendar_service_initialized': self.calendar_service is not None,
            'last_sync_time': self.last_sync_time,
            'timestamp': datetime.now().isoformat()
        }

def test_calendar_event_integration():
    """Test the calendar event integration."""
    try:
        logger.info("🧪 Testing calendar event integration...")
        
        # Initialize service
        service = EventDrivenCalendarService(enable_events=True)
        
        # Test calendar initialization
        if service.initialize_google_calendar():
            logger.info("✅ Google Calendar initialization successful")
        else:
            logger.error("❌ Google Calendar initialization failed")
            return False
        
        # Test event subscription
        if service.start_event_subscription():
            logger.info("✅ Event subscription test successful")
            
            # Stop subscription after test
            time.sleep(2)
            service.stop_event_subscription()
            
            return True
        else:
            logger.error("❌ Event subscription test failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Calendar event integration test error: {e}")
        return False

def integrate_with_flask_app(app):
    """Integration function for Flask app."""
    logger.info("🔗 Integrating event system with Flask calendar service...")
    
    # Create event-driven service
    calendar_service = EventDrivenCalendarService()
    
    # Start event subscription
    calendar_service.start_event_subscription()
    
    # Add status endpoint
    @app.route('/event-status', methods=['GET'])
    def event_status():
        return calendar_service.get_status()
    
    logger.info("✅ Event-driven calendar service integrated with Flask app")
    return calendar_service

def main():
    """Main function for standalone execution."""
    logger.info("🚀 Starting Event-Driven Calendar Service")
    
    # Initialize service
    service = EventDrivenCalendarService()
    
    # Initialize Google Calendar
    if not service.initialize_google_calendar():
        logger.error("❌ Failed to initialize Google Calendar")
        return False
    
    # Start event subscription
    if not service.start_event_subscription():
        logger.error("❌ Failed to start event subscription")
        return False
    
    logger.info("✅ Event-driven calendar service started successfully")
    logger.info("Service is now listening for match events...")
    
    try:
        # Keep service running
        while True:
            time.sleep(60)
            logger.debug("Event-driven calendar service running...")
    except KeyboardInterrupt:
        logger.info("Shutting down event-driven calendar service...")
        service.stop_event_subscription()
    
    return True

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
