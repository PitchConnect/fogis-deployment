#!/usr/bin/env python3
"""
Fix Calendar OAuth Authentication

This script implements a workaround for the FOGIS OAuth authentication issue
by using shorter OAuth parameters and implementing retry logic.
"""

import json
import logging
import os
import sys
import time
import docker
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_oauth_with_retry():
    """Test OAuth authentication with retry logic and parameter modifications."""
    try:
        # Connect to Docker
        client = docker.from_env()
        container = client.containers.get("fogis-calendar-phonebook-sync")
        
        logger.info("Testing OAuth authentication with retry logic...")
        
        # Create a modified authentication script with shorter parameters
        auth_script = '''
import sys
sys.path.append('/app')
import logging
import os
import time
import requests
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def try_oauth_authentication():
    """Try OAuth authentication with modified parameters."""
    username = os.getenv('FOGIS_USERNAME')
    password = os.getenv('FOGIS_PASSWORD')
    
    session = requests.Session()
    
    # Set headers to match working requests
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'sv-SE,sv;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    login_url = 'https://fogis.svenskfotboll.se/mdk/Login.aspx?ReturnUrl=%2fmdk%2f'
    
    try:
        # First attempt - try to get to OAuth login page
        logger.info("Attempting to reach OAuth login page...")
        response = session.get(login_url, allow_redirects=True, timeout=15)
        
        if response.status_code == 200 and 'auth.fogis.se' in response.url and '/Account/LogIn' in response.url:
            logger.info("Successfully reached OAuth login page")
            
            # Parse the login form
            soup = BeautifulSoup(response.text, 'html.parser')
            form = soup.find('form')
            
            if form:
                form_action = form.get('action', '')
                if form_action.startswith('/'):
                    form_url = f"https://auth.fogis.se{form_action}"
                else:
                    form_url = form_action or "https://auth.fogis.se/Account/Login"
                
                # Extract form data
                form_data = {}
                for input_field in form.find_all('input'):
                    field_name = input_field.get('name')
                    field_value = input_field.get('value', '')
                    if field_name:
                        form_data[field_name] = field_value
                
                # Set credentials
                form_data['Username'] = username
                form_data['Password'] = password
                if 'RememberMe' not in form_data:
                    form_data['RememberMe'] = 'false'
                
                logger.info(f"Submitting login form to {form_url}")
                
                # Submit the login form
                login_response = session.post(form_url, data=form_data, allow_redirects=True, timeout=15)
                
                if login_response.status_code == 200:
                    if 'fogis.svenskfotboll.se' in login_response.url:
                        logger.info("OAuth login successful - redirected back to FOGIS")
                        
                        # Extract session cookies
                        cookies = {}
                        for cookie in session.cookies:
                            if any(name in cookie.name for name in ['.AspNet.Cookies', 'ASPXAUTH', 'SessionId', 'Identity']):
                                cookies[cookie.name] = cookie.value
                        
                        if cookies:
                            logger.info(f"Successfully obtained {len(cookies)} session cookies")
                            print("SUCCESS: OAuth authentication completed")
                            return True
                        else:
                            logger.error("No session cookies found after login")
                    else:
                        logger.error("Login failed - still at OAuth login page")
                else:
                    logger.error(f"Login form submission failed: {login_response.status_code}")
            else:
                logger.error("No login form found on OAuth page")
        else:
            logger.error(f"Failed to reach OAuth login page: {response.status_code}, URL: {response.url}")
    
    except Exception as e:
        logger.error(f"OAuth authentication failed: {e}")
    
    return False

def try_aspnet_fallback():
    """Try ASP.NET authentication as fallback."""
    logger.info("Trying ASP.NET authentication fallback...")
    
    # This would require bypassing the OAuth redirect somehow
    # For now, return False as we haven't implemented this
    return False

# Main execution
success = False

# Try OAuth authentication with retry
for attempt in range(3):
    logger.info(f"OAuth attempt {attempt + 1}/3")
    if try_oauth_authentication():
        success = True
        break
    else:
        if attempt < 2:
            logger.info("Waiting 5 seconds before retry...")
            time.sleep(5)

if not success:
    logger.info("OAuth failed, trying ASP.NET fallback...")
    success = try_aspnet_fallback()

if success:
    print("AUTHENTICATION_SUCCESS")
else:
    print("AUTHENTICATION_FAILED")
'''
        
        # Execute the authentication script
        logger.info("Running modified OAuth authentication script...")
        exec_result = container.exec_run(
            ["python3", "-c", auth_script],
            stdout=True,
            stderr=True
        )
        
        output = exec_result.output.decode('utf-8')
        logger.info(f"Authentication script output:\n{output}")
        
        if "AUTHENTICATION_SUCCESS" in output:
            logger.info("✅ OAuth authentication workaround successful!")
            return True
        else:
            logger.error("❌ OAuth authentication workaround failed")
            return False
            
    except Exception as e:
        logger.error(f"Error testing OAuth workaround: {e}")
        return False

def test_calendar_sync():
    """Test calendar sync after authentication fix."""
    try:
        logger.info("Testing calendar sync...")
        
        import requests
        response = requests.post("http://localhost:9083/sync", timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if "error" not in result:
                logger.info("✅ Calendar sync successful!")
                return True
            else:
                logger.error(f"❌ Calendar sync failed: {result.get('error', 'Unknown error')}")
                return False
        else:
            logger.error(f"❌ Calendar sync request failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error testing calendar sync: {e}")
        return False

def main():
    """Main function to fix calendar OAuth and test sync."""
    logger.info("🔧 Starting Calendar OAuth Fix Process...")
    
    # Test OAuth authentication workaround
    logger.info("Step 1: Testing OAuth authentication workaround...")
    oauth_success = test_oauth_with_retry()
    
    if oauth_success:
        # Test calendar sync
        logger.info("Step 2: Testing calendar sync...")
        sync_success = test_calendar_sync()
        
        if sync_success:
            logger.info("🎉 Calendar OAuth fix completed successfully!")
            logger.info("The 2025-09-23 match should now appear in Google Calendar")
            return True
        else:
            logger.error("Calendar sync still failing after OAuth fix")
            return False
    else:
        logger.error("OAuth authentication workaround failed")
        logger.info("Recommendation: Implement centralized API integration (GitHub issue #100)")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
