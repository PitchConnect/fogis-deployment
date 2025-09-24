#!/usr/bin/env python3
"""
Refresh Google Calendar OAuth Token

This script attempts to refresh the expired Google Calendar OAuth token
for the fogis-calendar-phonebook-sync service.
"""

import json
import logging
import sys
import docker

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def refresh_calendar_token():
    """Refresh the Google Calendar OAuth token in the calendar service container."""
    try:
        # Connect to Docker
        client = docker.from_env()
        
        # Get the calendar service container
        container_name = "fogis-calendar-phonebook-sync"
        container = client.containers.get(container_name)
        
        logger.info(f"Found container: {container_name}")
        
        # Create a Python script to refresh the token
        refresh_script = '''
import sys
sys.path.append('/app')

import json
import logging
from token_manager import TokenManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # Load config
    with open('/app/config.json', 'r') as f:
        config = json.load(f)
    
    logger.info("Loaded configuration")
    
    # Initialize token manager
    token_manager = TokenManager(
        config=config,
        credentials_file='/app/credentials.json',
        token_file='/app/data/google-calendar/token.json'
    )
    
    logger.info("Initialized token manager")
    
    # Try to get credentials (this will trigger refresh if needed)
    credentials = token_manager.get_credentials()
    
    if credentials and credentials.valid:
        logger.info("✅ Token refresh successful!")
        print("SUCCESS: Token refreshed successfully")
    else:
        logger.error("❌ Token refresh failed")
        print("FAILED: Token refresh failed")
        
except Exception as e:
    logger.error(f"Error during token refresh: {e}")
    print(f"ERROR: {e}")
'''
        
        # Write the script to the container
        logger.info("Creating token refresh script in container...")
        exec_result = container.exec_run(
            ["python3", "-c", refresh_script],
            stdout=True,
            stderr=True
        )
        
        output = exec_result.output.decode('utf-8')
        logger.info(f"Script output: {output}")
        
        if "SUCCESS" in output:
            logger.info("✅ Token refresh completed successfully")
            return True
        else:
            logger.error(f"❌ Token refresh failed: {output}")
            return False
            
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        return False

def check_token_status():
    """Check the current token status."""
    try:
        client = docker.from_env()
        container = client.containers.get("fogis-calendar-phonebook-sync")
        
        # Check current token status
        exec_result = container.exec_run(
            ["python3", "-c", """
import json
from datetime import datetime

try:
    with open('/app/data/google-calendar/token.json', 'r') as f:
        token_data = json.load(f)
    
    expiry = datetime.fromisoformat(token_data['expiry'].replace('Z', '+00:00'))
    now = datetime.now(expiry.tzinfo)
    
    if expiry > now:
        hours_until_expiry = (expiry - now).total_seconds() / 3600
        print(f"Token is valid for {hours_until_expiry:.1f} more hours")
    else:
        hours_expired = (now - expiry).total_seconds() / 3600
        print(f"Token expired {hours_expired:.1f} hours ago")
        
except Exception as e:
    print(f"Error checking token: {e}")
"""],
            stdout=True,
            stderr=True
        )
        
        output = exec_result.output.decode('utf-8').strip()
        logger.info(f"Token status: {output}")
        return output
        
    except Exception as e:
        logger.error(f"Error checking token status: {e}")
        return None

if __name__ == "__main__":
    logger.info("🔄 Starting Google Calendar token refresh process...")
    
    # Check current status
    logger.info("📊 Checking current token status...")
    status = check_token_status()
    
    # Attempt refresh
    logger.info("🔄 Attempting token refresh...")
    success = refresh_calendar_token()
    
    if success:
        # Check status after refresh
        logger.info("📊 Checking token status after refresh...")
        new_status = check_token_status()
        
        logger.info("✅ Token refresh process completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Token refresh process failed!")
        sys.exit(1)
