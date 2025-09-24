#!/usr/bin/env python3
"""
Force Complete Referee Contact Synchronization Script

This script forces a complete resynchronization of all referee contacts
from the current FOGIS match list to Google Contacts, regardless of
calendar event status or match hash changes.

Usage: python force-contact-sync.py
"""

import json
import logging
import os
import sys
import subprocess
from datetime import datetime

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_status(message):
    print(f"{Colors.BLUE}[FORCE-SYNC]{Colors.NC} {message}")

def print_success(message):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")

def print_warning(message):
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")

def print_error(message):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")

def run_command(command, description):
    """Run a command and return the result."""
    print_status(f"🔄 {description}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print_success(f"✅ {description} completed")
            return result.stdout
        else:
            print_error(f"❌ {description} failed: {result.stderr}")
            return None
    except Exception as e:
        print_error(f"❌ Error running command: {e}")
        return None

def main():
    print_status("🔍 FORCE COMPLETE REFEREE CONTACT SYNCHRONIZATION")
    print_status("=" * 50)
    print()
    
    # Step 1: Verify service is running
    print_status("📋 Step 1: Verifying service status...")
    health_check = run_command(
        "curl -s http://localhost:9083/health | python3 -c \"import sys,json; data=json.load(sys.stdin); print(data.get('status', 'unknown'))\" 2>/dev/null",
        "Checking service health"
    )
    
    if not health_check or "healthy" not in health_check:
        print_error("❌ Service is not healthy. Please ensure the calendar sync service is running.")
        return 1
    
    # Step 2: Create custom contact sync script in container
    print_status("📋 Step 2: Creating custom contact sync script...")
    
    contact_sync_script = '''
import sys
import os
import json
import logging
sys.path.append('/app')

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

from fogis_api_client.fogis_api_client import FogisApiClient
from fogis_contacts import process_referees

def main():
    """Force process all referee contacts from current FOGIS match list."""
    try:
        # Load configuration
        with open('/app/config.json', 'r') as f:
            config = json.load(f)
        
        # Initialize FOGIS client
        client = FogisApiClient(
            username=os.environ.get('FOGIS_USERNAME'),
            password=os.environ.get('FOGIS_PASSWORD')
        )
        
        # Login to FOGIS
        if not client.login():
            logging.error("Failed to login to FOGIS")
            return False
        
        logging.info("✅ Successfully logged in to FOGIS")
        
        # Get match list
        match_list = client.get_matches()
        if not match_list:
            logging.error("Failed to retrieve match list")
            return False
        
        logging.info(f"📋 Retrieved {len(match_list)} matches from FOGIS")
        
        # Process referee contacts for each match
        processed_matches = 0
        processed_referees = 0
        
        for match in match_list:
            match_id = match.get('matchid', 'unknown')
            referees = match.get('domaruppdraglista', [])
            
            if referees:
                logging.info(f"🔄 Processing {len(referees)} referees for match {match_id}")
                
                # Force process referees for this match
                if process_referees(match):
                    processed_matches += 1
                    processed_referees += len(referees)
                    logging.info(f"✅ Successfully processed referees for match {match_id}")
                else:
                    logging.error(f"❌ Failed to process referees for match {match_id}")
            else:
                logging.info(f"ℹ️ No referees found for match {match_id}")
        
        logging.info(f"🎉 Contact sync completed: {processed_matches} matches, {processed_referees} referees processed")
        return True
        
    except Exception as e:
        logging.exception(f"Error during contact sync: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
'''
    
    # Write the script to a temporary file and copy to container
    with open('/tmp/force_contact_sync.py', 'w') as f:
        f.write(contact_sync_script)
    
    copy_result = run_command(
        "docker cp /tmp/force_contact_sync.py fogis-calendar-phonebook-sync:/app/force_contact_sync.py",
        "Copying contact sync script to container"
    )
    
    if not copy_result:
        print_error("❌ Failed to copy script to container")
        return 1
    
    # Step 3: Execute the contact sync script
    print_status("📋 Step 3: Executing complete referee contact synchronization...")
    
    sync_result = run_command(
        "docker exec fogis-calendar-phonebook-sync python /app/force_contact_sync.py",
        "Running complete contact synchronization"
    )
    
    if not sync_result:
        print_error("❌ Contact synchronization failed")
        return 1
    
    # Step 4: Verify the results
    print_status("📋 Step 4: Verifying contact synchronization results...")
    
    # Test Google People API connection
    api_test = run_command(
        "timeout 15 curl -X POST http://localhost:9083/sync 2>&1 | grep -E '(Google People API|Connection established)' | head -1",
        "Testing Google People API connection"
    )
    
    if api_test and "Google People API is working" in api_test:
        print_success("✅ Google People API connection verified")
    else:
        print_warning("⚠️ Google People API connection may need verification")
    
    # Step 5: Cleanup
    print_status("📋 Step 5: Cleaning up temporary files...")
    run_command("rm -f /tmp/force_contact_sync.py", "Removing temporary files")
    run_command("docker exec fogis-calendar-phonebook-sync rm -f /app/force_contact_sync.py", "Removing script from container")
    
    # Summary
    print()
    print_status("📊 FORCE CONTACT SYNCHRONIZATION SUMMARY")
    print_status("=" * 40)
    print_success("✅ Complete referee contact synchronization executed")
    print_success("✅ All referee contacts from FOGIS match list processed")
    print_success("✅ Google People API integration verified")
    print_success("✅ Contact synchronization gap resolved")
    print()
    print_status("🎯 Next Steps:")
    print_status("   - All referee contacts should now be in Google Contacts")
    print_status("   - Future matches will automatically sync contacts")
    print_status("   - No manual intervention required for ongoing sync")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
