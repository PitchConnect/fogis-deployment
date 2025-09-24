#!/usr/bin/env python3
"""
Calendar Sync Emergency Mode Patch

This script patches the calendar sync script to handle emergency mode
where match data is provided directly instead of fetching from FOGIS.

Author: System Architecture Team
Date: 2025-09-20
Issue: #100 - Calendar sync script emergency mode integration
"""

import json
import logging
import os
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def patch_calendar_sync_for_emergency_mode():
    """Patch the calendar sync script to handle emergency mode."""
    try:
        logger.info("🔧 Patching calendar sync script for emergency mode...")
        
        # Read the current script
        script_path = "/app/fogis_calendar_sync.py"
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Create backup
        backup_path = f"{script_path}.backup-emergency-{int(__import__('time').time())}"
        with open(backup_path, 'w') as f:
            f.write(content)
        logger.info(f"Created backup: {backup_path}")
        
        # Find the FOGIS authentication section and add emergency mode handling
        lines = content.split('\n')
        
        # Find the line with fogis_api_client.login()
        login_line_index = None
        for i, line in enumerate(lines):
            if 'cookies = fogis_api_client.login()' in line:
                login_line_index = i
                break
        
        if login_line_index is None:
            logger.error("Could not find FOGIS login line")
            return False
        
        # Insert emergency mode handling before the login
        emergency_code = [
            '',
            '    # Emergency Mode: Use provided match data instead of FOGIS authentication',
            '    if os.getenv("EMERGENCY_MODE") == "true":',
            '        emergency_file = os.getenv("EMERGENCY_MATCH_DATA_FILE")',
            '        if emergency_file and os.path.exists(emergency_file):',
            '            logger.info("🚨 Emergency mode activated - using provided match data")',
            '            logger.info(f"Loading match data from: {emergency_file}")',
            '            ',
            '            try:',
            '                with open(emergency_file, "r") as f:',
            '                    emergency_matches = json.load(f)',
            '                ',
            '                logger.info(f"Loaded {len(emergency_matches)} matches from emergency file")',
            '                ',
            '                # Find target match for logging',
            '                target_match = next((m for m in emergency_matches if m.get("speldatum") == "2025-09-23"), None)',
            '                if target_match:',
            '                    logger.info(f"🎯 Target match found: {target_match.get(\\"lag1namn\\")} vs {target_match.get(\\"lag2namn\\")} on 2025-09-23")',
            '                ',
            '                # Process matches for calendar sync',
            '                logger.info("Processing emergency matches for calendar sync...")',
            '                ',
            '                # Initialize Google Calendar service',
            '                calendar_service = get_calendar_service()',
            '                if not calendar_service:',
            '                    raise Exception("Failed to initialize Google Calendar service")',
            '                ',
            '                # Process each match',
            '                events_created = 0',
            '                for match in emergency_matches:',
            '                    try:',
            '                        # Use existing match processing logic',
            '                        if process_match_for_calendar(match, calendar_service):',
            '                            events_created += 1',
            '                    except Exception as e:',
            '                        logger.error(f"Failed to process match {match.get(\\"matchid\\")}: {e}")',
            '                ',
            '                logger.info(f"✅ Emergency mode completed: {events_created} events created")',
            '                return  # Exit early - emergency mode complete',
            '                ',
            '            except Exception as e:',
            '                logger.error(f"Emergency mode failed: {e}")',
            '                raise',
            '        else:',
            '            logger.error("Emergency mode enabled but no data file provided")',
            '            raise Exception("Emergency mode enabled but no data file provided")',
            '',
        ]
        
        # Insert the emergency code before the login line
        for i, code_line in enumerate(emergency_code):
            lines.insert(login_line_index + i, code_line)
        
        # Write the patched script
        patched_content = '\n'.join(lines)
        with open(script_path, 'w') as f:
            f.write(patched_content)
        
        logger.info("✅ Calendar sync script patched successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to patch calendar sync script: {e}")
        return False

def create_match_processing_function():
    """Create a helper function for processing individual matches."""
    helper_code = '''

def process_match_for_calendar(match, calendar_service):
    """
    Process a single match for calendar sync.
    
    Args:
        match: Match dictionary
        calendar_service: Google Calendar service instance
        
    Returns:
        bool: True if event was created/updated successfully
    """
    try:
        # Extract match details
        match_id = match.get('matchid')
        match_date = match.get('speldatum')
        match_time = match.get('avsparkstid', '00:00')
        team1 = match.get('lag1namn', 'Team 1')
        team2 = match.get('lag2namn', 'Team 2')
        venue = match.get('anlaggningnamn', 'Unknown venue')
        competition = match.get('tavlingnamn', 'Unknown competition')
        
        logger.info(f"Processing match: {team1} vs {team2} on {match_date} at {match_time}")
        
        # Create event title
        event_title = f"{team1} vs {team2}"
        
        # Create event description
        event_description = f"""
Match Details:
- Competition: {competition}
- Venue: {venue}
- Date: {match_date}
- Time: {match_time}
- Match ID: {match_id}

Generated by FOGIS Calendar Sync (Emergency Mode)
        """.strip()
        
        # Parse date and time
        from datetime import datetime, timedelta
        import pytz
        
        # Combine date and time
        datetime_str = f"{match_date} {match_time}"
        match_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        
        # Set timezone (assuming Swedish time)
        swedish_tz = pytz.timezone('Europe/Stockholm')
        match_datetime = swedish_tz.localize(match_datetime)
        
        # Event duration (assume 2 hours)
        end_datetime = match_datetime + timedelta(hours=2)
        
        # Create event
        event = {
            'summary': event_title,
            'description': event_description,
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
        
        # Insert event into calendar
        calendar_id = 'primary'  # Use primary calendar
        created_event = calendar_service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()
        
        logger.info(f"✅ Created calendar event: {created_event.get('id')}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to process match {match.get('matchid', 'unknown')}: {e}")
        return False

def get_calendar_service():
    """Get Google Calendar service instance."""
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        
        # Load credentials from token file
        token_file = '/app/data/google-calendar/token.json'
        
        if not os.path.exists(token_file):
            logger.error(f"Token file not found: {token_file}")
            return None
        
        with open(token_file, 'r') as f:
            token_data = json.load(f)
        
        # Create credentials object
        credentials = Credentials(
            token=token_data.get('token'),
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_data.get('token_uri'),
            client_id=token_data.get('client_id'),
            client_secret=token_data.get('client_secret'),
            scopes=token_data.get('scopes', [])
        )
        
        # Build calendar service
        service = build('calendar', 'v3', credentials=credentials)
        logger.info("✅ Google Calendar service initialized")
        return service
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Google Calendar service: {e}")
        return None
'''
    
    return helper_code

def apply_complete_patch():
    """Apply the complete emergency mode patch."""
    try:
        logger.info("🚨 Applying complete emergency mode patch...")
        
        # First, patch the main function
        if not patch_calendar_sync_for_emergency_mode():
            return False
        
        # Add helper functions
        helper_code = create_match_processing_function()
        
        # Append helper functions to the script
        script_path = "/app/fogis_calendar_sync.py"
        with open(script_path, 'a') as f:
            f.write(helper_code)
        
        logger.info("✅ Complete emergency mode patch applied successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to apply complete patch: {e}")
        return False

def test_emergency_mode():
    """Test the emergency mode patch."""
    try:
        logger.info("🧪 Testing emergency mode patch...")
        
        # Create test match data
        test_matches = [
            {
                "matchid": 6491192,
                "speldatum": "2025-09-23",
                "avsparkstid": "19:00",
                "lag1namn": "Jitex BK",
                "lag2namn": "Vittsjö GIK",
                "tavlingnamn": "Svenska Cupen 2025/26 omg. 1-3",
                "anlaggningnamn": "Åbyvallen 1 Konstgräs"
            }
        ]
        
        # Save test data
        test_file = "/tmp/emergency_test_matches.json"
        with open(test_file, 'w') as f:
            json.dump(test_matches, f, indent=2)
        
        # Set up environment
        env = os.environ.copy()
        env['EMERGENCY_MODE'] = 'true'
        env['EMERGENCY_MATCH_DATA_FILE'] = test_file
        
        # Run the patched script
        cmd = ['python', 'fogis_calendar_sync.py', '--headless']
        logger.info(f"Running patched script: {' '.join(cmd)}")
        
        process = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            cwd='/app'
        )
        
        logger.info(f"Return code: {process.returncode}")
        logger.info(f"STDOUT: {process.stdout}")
        if process.stderr:
            logger.info(f"STDERR: {process.stderr}")
        
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
        
        if process.returncode == 0:
            logger.info("✅ Emergency mode test successful!")
            return True
        else:
            logger.error("❌ Emergency mode test failed")
            return False
        
    except Exception as e:
        logger.error(f"❌ Emergency mode test error: {e}")
        return False

def main():
    """Main function."""
    logger.info("🚨 Calendar Sync Emergency Mode Patch")
    logger.info("This will patch the calendar sync script to handle emergency mode")
    logger.info("")
    
    # Apply patch
    if apply_complete_patch():
        logger.info("✅ Patch applied successfully")
        
        # Test patch
        if test_emergency_mode():
            logger.info("🎉 Emergency mode patch completed and tested successfully!")
            logger.info("")
            logger.info("📋 The calendar sync script now supports:")
            logger.info("   ✅ Emergency mode with EMERGENCY_MODE=true")
            logger.info("   ✅ Direct match data processing")
            logger.info("   ✅ Google Calendar integration")
            logger.info("   ✅ Bypass of FOGIS OAuth authentication")
            return True
        else:
            logger.error("❌ Patch test failed")
            return False
    else:
        logger.error("❌ Patch application failed")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
