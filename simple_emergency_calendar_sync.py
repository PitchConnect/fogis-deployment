#!/usr/bin/env python3
"""
Simple Emergency Calendar Sync

This script provides a simple, working calendar sync that processes
emergency match data and adds events to Google Calendar.

Author: System Architecture Team
Date: 2025-09-20
Issue: #100 - Emergency calendar sync implementation
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_emergency_match_data(file_path: str) -> List[Dict]:
    """Load match data from emergency file."""
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Emergency data file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            matches = json.load(f)
        
        logger.info(f"✅ Loaded {len(matches)} matches from emergency file")
        return matches
        
    except Exception as e:
        logger.error(f"❌ Failed to load emergency data: {e}")
        raise

def get_google_calendar_service():
    """Initialize Google Calendar service."""
    try:
        # Import Google API libraries
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
        service = build('calendar', 'v3', credentials=credentials)
        logger.info("✅ Google Calendar service initialized")
        return service
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Google Calendar service: {e}")
        raise

def create_calendar_event(match: Dict, calendar_service) -> bool:
    """Create a calendar event for a match."""
    try:
        # Extract match details
        match_id = match.get('matchid', 'unknown')
        match_date = match.get('speldatum')
        match_time = match.get('avsparkstid', '00:00')
        team1 = match.get('lag1namn', 'Team 1')
        team2 = match.get('lag2namn', 'Team 2')
        venue = match.get('anlaggningnamn', 'Unknown venue')
        competition = match.get('tavlingnamn', 'Unknown competition')
        
        logger.info(f"Creating event: {team1} vs {team2} on {match_date} at {match_time}")
        
        # Parse datetime
        datetime_str = f"{match_date} {match_time}"
        try:
            match_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        except ValueError:
            # Try alternative format
            match_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        
        # Set timezone (Swedish time)
        import pytz
        swedish_tz = pytz.timezone('Europe/Stockholm')
        match_datetime = swedish_tz.localize(match_datetime)
        
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

🚨 Added via Emergency Calendar Sync
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
        created_event = calendar_service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()
        
        event_id = created_event.get('id')
        event_link = created_event.get('htmlLink', 'N/A')
        
        logger.info(f"✅ Created calendar event: {event_id}")
        logger.info(f"   Event link: {event_link}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create event for match {match.get('matchid', 'unknown')}: {e}")
        return False

def process_emergency_matches(matches: List[Dict]) -> Dict[str, Any]:
    """Process emergency matches and create calendar events."""
    try:
        logger.info(f"🚨 Processing {len(matches)} emergency matches...")
        
        # Initialize Google Calendar service
        calendar_service = get_google_calendar_service()
        
        # Process each match
        events_created = 0
        events_failed = 0
        
        for match in matches:
            try:
                if create_calendar_event(match, calendar_service):
                    events_created += 1
                else:
                    events_failed += 1
            except Exception as e:
                logger.error(f"Failed to process match {match.get('matchid', 'unknown')}: {e}")
                events_failed += 1
        
        result = {
            'status': 'success' if events_created > 0 else 'failed',
            'matches_processed': len(matches),
            'events_created': events_created,
            'events_failed': events_failed,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Emergency sync completed: {events_created} events created, {events_failed} failed")
        return result
        
    except Exception as e:
        logger.error(f"❌ Emergency match processing failed: {e}")
        raise

def main():
    """Main emergency calendar sync function."""
    try:
        logger.info("🚨 Starting Simple Emergency Calendar Sync")
        
        # Check for emergency mode
        if os.getenv('EMERGENCY_MODE') != 'true':
            logger.error("❌ Emergency mode not enabled (EMERGENCY_MODE != 'true')")
            return False
        
        # Get emergency data file
        emergency_file = os.getenv('EMERGENCY_MATCH_DATA_FILE')
        if not emergency_file:
            logger.error("❌ No emergency data file specified (EMERGENCY_MATCH_DATA_FILE not set)")
            return False
        
        logger.info(f"📁 Emergency data file: {emergency_file}")
        
        # Load match data
        matches = load_emergency_match_data(emergency_file)
        
        # Log target match
        target_match = next((m for m in matches if m.get('speldatum') == '2025-09-23'), None)
        if target_match:
            team1 = target_match.get('lag1namn', 'Unknown')
            team2 = target_match.get('lag2namn', 'Unknown')
            match_time = target_match.get('avsparkstid', 'Unknown')
            logger.info(f"🎯 Target match found: {team1} vs {team2} on 2025-09-23 at {match_time}")
        
        # Process matches
        result = process_emergency_matches(matches)
        
        if result['status'] == 'success':
            logger.info("🎉 Emergency calendar sync completed successfully!")
            logger.info(f"   Events created: {result['events_created']}")
            logger.info(f"   Matches processed: {result['matches_processed']}")
            
            if target_match and result['events_created'] > 0:
                logger.info("🎯 The 2025-09-23 match should now be visible in Google Calendar!")
            
            return True
        else:
            logger.error("❌ Emergency calendar sync failed")
            return False
        
    except Exception as e:
        logger.error(f"❌ Emergency calendar sync error: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
