#!/usr/bin/env python3
"""
Calendar Sync with Retry Logic

This script implements a robust calendar sync with retry logic to handle
the intermittent OAuth authentication failures.
"""

import json
import logging
import requests
import time
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calendar_sync_with_retry(max_retries=5, base_delay=5):
    """
    Perform calendar sync with retry logic to handle OAuth failures.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries (will use exponential backoff)
    
    Returns:
        bool: True if sync was successful, False otherwise
    """
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Calendar sync attempt {attempt + 1}/{max_retries}")
            
            # Make the sync request
            response = requests.post(
                "http://localhost:9083/sync",
                timeout=60  # Increased timeout for OAuth operations
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Check if the response indicates success
                if "error" not in result:
                    logger.info("✅ Calendar sync completed successfully!")
                    logger.info("Response: %s", result)
                    return True
                
                # Check if it's an OAuth error that we can retry
                error_msg = result.get("error", "")
                if "400 Client Error: Bad Rquest" in error_msg:
                    logger.warning(f"OAuth authentication failed on attempt {attempt + 1}")
                    logger.warning("This is the intermittent OAuth issue - will retry")
                elif "FOGIS sync failed" in error_msg:
                    logger.warning(f"FOGIS sync failed on attempt {attempt + 1}")
                    logger.warning("Error details: %s", error_msg[:500] + "..." if len(error_msg) > 500 else error_msg)
                else:
                    logger.error(f"Unexpected error on attempt {attempt + 1}: {error_msg}")
                    
            else:
                logger.warning(f"HTTP error on attempt {attempt + 1}: {response.status_code}")
                if response.text:
                    logger.warning(f"Response: {response.text[:200]}...")
            
            # If this isn't the last attempt, wait before retrying
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Waiting {delay} seconds before retry...")
                time.sleep(delay)
                
        except requests.exceptions.Timeout:
            logger.warning(f"Request timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.info(f"Waiting {delay} seconds before retry...")
                time.sleep(delay)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.info(f"Waiting {delay} seconds before retry...")
                time.sleep(delay)
                
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.info(f"Waiting {delay} seconds before retry...")
                time.sleep(delay)
    
    logger.error(f"❌ Calendar sync failed after {max_retries} attempts")
    return False

def check_calendar_service_health():
    """Check if the calendar service is healthy."""
    try:
        response = requests.get("http://localhost:9083/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            logger.info("Calendar service health: %s", health_data.get("status", "unknown"))
            
            # Check OAuth token status
            oauth_info = health_data.get("oauth_info", {})
            expires_in = oauth_info.get("expires_in_hours", 0)
            
            if expires_in > 0:
                logger.info(f"Google Calendar token is valid for {expires_in:.1f} hours")
            else:
                logger.warning(f"Google Calendar token expired {abs(expires_in):.1f} hours ago")
                
            return True
        else:
            logger.error(f"Calendar service health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error checking calendar service health: {e}")
        return False

def verify_match_data():
    """Verify that the 2025-09-23 match data is available."""
    try:
        logger.info("Verifying match data availability...")
        
        # Check centralized FOGIS API
        response = requests.get("http://localhost:9086/matches", timeout=15)
        if response.status_code == 200:
            matches = response.json()
            
            # Look for the 2025-09-23 match
            target_match = None
            for match in matches:
                if match.get("speldatum") == "2025-09-23":
                    target_match = match
                    break
            
            if target_match:
                logger.info("✅ Target match found in FOGIS API:")
                logger.info(f"   Match: {target_match.get('lag1namn')} vs {target_match.get('lag2namn')}")
                logger.info(f"   Date: {target_match.get('speldatum')} at {target_match.get('avsparkstid')}")
                logger.info(f"   Competition: {target_match.get('tavlingnamn')}")
                logger.info(f"   Venue: {target_match.get('anlaggningnamn')}")
                return True
            else:
                logger.warning("❌ Target match (2025-09-23) not found in FOGIS API")
                return False
        else:
            logger.error(f"Failed to fetch matches from FOGIS API: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying match data: {e}")
        return False

def main():
    """Main function to perform calendar sync with retry logic."""
    logger.info("🔄 Starting Calendar Sync with Retry Logic...")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Step 1: Check calendar service health
    logger.info("Step 1: Checking calendar service health...")
    if not check_calendar_service_health():
        logger.error("Calendar service is not healthy")
        return False
    
    # Step 2: Verify match data
    logger.info("Step 2: Verifying match data availability...")
    if not verify_match_data():
        logger.error("Match data verification failed")
        return False
    
    # Step 3: Perform calendar sync with retry
    logger.info("Step 3: Performing calendar sync with retry logic...")
    success = calendar_sync_with_retry(max_retries=5, base_delay=5)
    
    if success:
        logger.info("🎉 Calendar sync completed successfully!")
        logger.info("The 2025-09-23 match should now appear in Google Calendar")
        
        # Verify the sync worked by checking the service again
        logger.info("Step 4: Verifying sync completion...")
        time.sleep(2)
        check_calendar_service_health()
        
        return True
    else:
        logger.error("❌ Calendar sync failed after all retry attempts")
        logger.info("Possible solutions:")
        logger.info("1. Implement centralized API integration (GitHub issue #100)")
        logger.info("2. Check FOGIS server status and OAuth endpoint availability")
        logger.info("3. Review OAuth parameter generation in FOGIS API client")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
