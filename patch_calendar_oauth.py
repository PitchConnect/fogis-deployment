#!/usr/bin/env python3
"""
Patch Calendar OAuth Authentication

This script patches the calendar service's FOGIS API client to implement
retry logic and parameter optimization to resolve the intermittent OAuth failures.
"""

import logging
import docker
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def patch_oauth_authentication():
    """Patch the OAuth authentication in the calendar service."""
    try:
        # Connect to Docker
        client = docker.from_env()
        container = client.containers.get("fogis-calendar-phonebook-sync")
        
        logger.info("Patching OAuth authentication with retry logic...")
        
        # Create a patched authentication module
        patch_script = '''
import sys
import os
import time
import logging

# Patch the FOGIS API client to add retry logic
def patch_fogis_client():
    """Patch the FOGIS API client with retry logic."""
    
    # Import the original modules
    sys.path.append('/usr/local/lib/python3.11/site-packages')
    from fogis_api_client import fogis_api_client
    
    # Store the original login method
    original_login = fogis_api_client.FogisApiClient.login
    
    def login_with_retry(self):
        """Login with retry logic to handle intermittent OAuth failures."""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"OAuth login attempt {attempt + 1}/{max_retries}")
                
                # Call the original login method
                result = original_login(self)
                
                self.logger.info("OAuth login successful")
                return result
                
            except Exception as e:
                error_msg = str(e)
                
                # Check if it's the specific OAuth 400 error
                if "400 Client Error: Bad Rquest" in error_msg and attempt < max_retries - 1:
                    self.logger.warning(f"OAuth attempt {attempt + 1} failed with 400 error, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    # Re-raise the exception if it's not the OAuth error or we've exhausted retries
                    self.logger.error(f"OAuth login failed after {attempt + 1} attempts: {error_msg}")
                    raise
        
        # This should never be reached, but just in case
        raise Exception("OAuth login failed after all retry attempts")
    
    # Replace the login method with our patched version
    fogis_api_client.FogisApiClient.login = login_with_retry
    
    print("PATCH_APPLIED: OAuth retry logic installed")

# Apply the patch
try:
    patch_fogis_client()
    print("SUCCESS: OAuth authentication patched")
except Exception as e:
    print(f"ERROR: Failed to patch OAuth authentication: {e}")
'''
        
        # Apply the patch
        logger.info("Applying OAuth retry patch...")
        exec_result = container.exec_run(
            ["python3", "-c", patch_script],
            stdout=True,
            stderr=True
        )
        
        output = exec_result.output.decode('utf-8')
        logger.info(f"Patch output: {output}")
        
        if "SUCCESS: OAuth authentication patched" in output:
            logger.info("✅ OAuth authentication patch applied successfully")
            return True
        else:
            logger.error("❌ Failed to apply OAuth authentication patch")
            return False
            
    except Exception as e:
        logger.error(f"Error patching OAuth authentication: {e}")
        return False

def restart_calendar_service():
    """Restart the calendar service to apply patches."""
    try:
        logger.info("Restarting calendar service to apply patches...")
        
        import subprocess
        result = subprocess.run(
            ["docker", "restart", "fogis-calendar-phonebook-sync"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logger.info("✅ Calendar service restarted successfully")
            
            # Wait for service to be ready
            logger.info("Waiting for service to be ready...")
            time.sleep(10)
            
            return True
        else:
            logger.error(f"❌ Failed to restart calendar service: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error restarting calendar service: {e}")
        return False

def test_calendar_sync_with_patch():
    """Test calendar sync after applying the patch."""
    try:
        logger.info("Testing calendar sync with OAuth patch...")
        
        import requests
        
        # Test multiple times to verify the patch works
        for attempt in range(3):
            logger.info(f"Calendar sync test {attempt + 1}/3")
            
            try:
                response = requests.post("http://localhost:9083/sync", timeout=45)
                
                if response.status_code == 200:
                    result = response.json()
                    if "error" not in result or "FOGIS sync failed" not in result.get("error", ""):
                        logger.info(f"✅ Calendar sync successful on attempt {attempt + 1}")
                        return True
                    else:
                        logger.warning(f"Calendar sync attempt {attempt + 1} failed: {result.get('error', 'Unknown error')}")
                else:
                    logger.warning(f"Calendar sync attempt {attempt + 1} failed with status {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"Calendar sync attempt {attempt + 1} failed with exception: {e}")
            
            if attempt < 2:
                logger.info("Waiting 10 seconds before next attempt...")
                time.sleep(10)
        
        logger.error("❌ All calendar sync attempts failed")
        return False
        
    except Exception as e:
        logger.error(f"Error testing calendar sync: {e}")
        return False

def main():
    """Main function to patch OAuth and test calendar sync."""
    logger.info("🔧 Starting Calendar OAuth Patch Process...")
    
    # Apply OAuth patch
    logger.info("Step 1: Applying OAuth retry patch...")
    patch_success = patch_oauth_authentication()
    
    if not patch_success:
        logger.error("Failed to apply OAuth patch")
        return False
    
    # Restart service
    logger.info("Step 2: Restarting calendar service...")
    restart_success = restart_calendar_service()
    
    if not restart_success:
        logger.error("Failed to restart calendar service")
        return False
    
    # Test calendar sync
    logger.info("Step 3: Testing calendar sync with patch...")
    sync_success = test_calendar_sync_with_patch()
    
    if sync_success:
        logger.info("🎉 Calendar OAuth patch completed successfully!")
        logger.info("The 2025-09-23 match should now appear in Google Calendar")
        return True
    else:
        logger.error("Calendar sync still failing after patch")
        logger.info("Recommendation: Implement centralized API integration (GitHub issue #100)")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
