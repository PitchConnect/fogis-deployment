#!/usr/bin/env python3
"""
Integrate Emergency Calendar Notification

This script integrates emergency calendar notification into the match-list-processor
to send match data directly to the calendar service emergency endpoint.

Author: System Architecture Team
Date: 2025-09-19
Issue: #100 - OAuth authentication failures in calendar service
"""

import json
import logging
import requests
import time
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def notify_calendar_service_emergency(matches, calendar_service_url="http://fogis-calendar-phonebook-sync:9083"):
    """
    Send match data directly to calendar service emergency endpoint.
    
    Args:
        matches: List of match dictionaries
        calendar_service_url: URL of calendar service
        
    Returns:
        Dict containing notification results
    """
    try:
        # Prepare payload
        payload = {
            'matches': matches,
            'timestamp': datetime.now().isoformat(),
            'source': 'match-list-processor-emergency',
            'metadata': {
                'total_matches': len(matches),
                'notification_time': datetime.now().isoformat()
            }
        }
        
        # Add request tracking
        request_id = f"emergency-{int(time.time())}"
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'match-list-processor/emergency-client',
            'X-Request-ID': request_id
        }
        
        logger.info(f"🚨 Sending emergency calendar notification: {len(matches)} matches (Request ID: {request_id})")
        
        # Log specific target match
        target_match = next((m for m in matches if m.get('speldatum') == '2025-09-23'), None)
        if target_match:
            logger.info(f"🎯 Target match included: {target_match.get('lag1namn')} vs {target_match.get('lag2namn')} on 2025-09-23")
        
        # Send notification with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Emergency notification attempt {attempt + 1}/{max_retries}")
                
                response = requests.post(
                    f"{calendar_service_url}/sync-with-data",
                    json=payload,
                    headers=headers,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✅ Emergency notification successful: {result.get('events_created', 0)} events created")
                    
                    return {
                        'status': 'success',
                        'attempt': attempt + 1,
                        'request_id': request_id,
                        'calendar_response': result
                    }
                    
                else:
                    error_msg = f"Calendar service returned {response.status_code}: {response.text[:200]}"
                    logger.warning(error_msg)
                    
                    if attempt == max_retries - 1:
                        return {
                            'status': 'failed',
                            'attempts': max_retries,
                            'request_id': request_id,
                            'last_error': error_msg
                        }
                    
            except requests.exceptions.Timeout:
                error_msg = f"Request timeout after 60s (attempt {attempt + 1})"
                logger.warning(error_msg)
                
                if attempt == max_retries - 1:
                    return {
                        'status': 'failed',
                        'attempts': max_retries,
                        'request_id': request_id,
                        'last_error': error_msg
                    }
                    
            except requests.exceptions.ConnectionError as e:
                error_msg = f"Connection error to calendar service (attempt {attempt + 1}): {e}"
                logger.warning(error_msg)
                
                if attempt == max_retries - 1:
                    return {
                        'status': 'failed',
                        'attempts': max_retries,
                        'request_id': request_id,
                        'last_error': error_msg
                    }
                    
            except Exception as e:
                error_msg = f"Unexpected error in emergency notification (attempt {attempt + 1}): {e}"
                logger.error(error_msg, exc_info=True)
                
                if attempt == max_retries - 1:
                    return {
                        'status': 'failed',
                        'attempts': max_retries,
                        'request_id': request_id,
                        'last_error': error_msg
                    }
            
            # Wait before retry (exponential backoff)
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
        
    except Exception as e:
        logger.error(f"❌ Emergency notification failed: {e}", exc_info=True)
        return {
            'status': 'failed',
            'attempts': 0,
            'request_id': 'unknown',
            'last_error': str(e)
        }

def test_emergency_notification():
    """Test the emergency notification with sample data."""
    try:
        logger.info("🧪 Testing emergency calendar notification...")
        
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
        
        # Test notification
        result = notify_calendar_service_emergency(test_matches)
        
        if result['status'] == 'success':
            logger.info("✅ Emergency notification test successful!")
            return True
        else:
            logger.error(f"❌ Emergency notification test failed: {result}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Emergency notification test error: {e}")
        return False

def get_current_matches():
    """
    Get current matches from the centralized FOGIS API.
    
    Returns:
        List of match dictionaries
    """
    try:
        logger.info("📊 Fetching current matches from centralized FOGIS API...")
        
        response = requests.get("http://fogis-api-client-service:8080/matches", timeout=30)
        
        if response.status_code == 200:
            matches = response.json()
            logger.info(f"✅ Retrieved {len(matches)} matches from FOGIS API")
            
            # Log if target match is present
            target_match = next((m for m in matches if m.get('speldatum') == '2025-09-23'), None)
            if target_match:
                logger.info(f"🎯 Target match found in FOGIS data: {target_match.get('lag1namn')} vs {target_match.get('lag2namn')}")
            
            return matches
        else:
            logger.error(f"❌ Failed to fetch matches: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"❌ Error fetching matches: {e}")
        return []

def run_emergency_sync():
    """Run emergency sync with current match data."""
    try:
        logger.info("🚨 Running emergency calendar sync...")
        
        # Get current matches
        matches = get_current_matches()
        
        if not matches:
            logger.error("❌ No matches available for sync")
            return False
        
        # Send emergency notification
        result = notify_calendar_service_emergency(matches)
        
        if result['status'] == 'success':
            logger.info("🎉 Emergency calendar sync completed successfully!")
            logger.info(f"   Events created: {result.get('calendar_response', {}).get('events_created', 0)}")
            logger.info(f"   Matches processed: {result.get('calendar_response', {}).get('matches_processed', 0)}")
            return True
        else:
            logger.error(f"❌ Emergency calendar sync failed: {result}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Emergency sync error: {e}")
        return False

def main():
    """Main function for emergency integration."""
    logger.info("🚨 Emergency Calendar Notification Integration")
    logger.info("This script integrates emergency calendar notification into match processing")
    logger.info("")
    
    # Test emergency notification
    logger.info("Step 1: Testing emergency notification...")
    if test_emergency_notification():
        logger.info("✅ Emergency notification test passed")
    else:
        logger.error("❌ Emergency notification test failed")
        return False
    
    logger.info("")
    
    # Run emergency sync with real data
    logger.info("Step 2: Running emergency sync with current match data...")
    if run_emergency_sync():
        logger.info("✅ Emergency sync completed successfully")
    else:
        logger.error("❌ Emergency sync failed")
        return False
    
    logger.info("")
    logger.info("🎉 Emergency calendar notification integration completed!")
    logger.info("")
    logger.info("📋 Integration Summary:")
    logger.info("   ✅ Emergency endpoint tested and working")
    logger.info("   ✅ Match data retrieved from FOGIS API")
    logger.info("   ✅ Calendar notification sent successfully")
    logger.info("   ✅ 2025-09-23 match should now be in Google Calendar")
    logger.info("")
    logger.info("🎯 Next Steps:")
    logger.info("1. Verify match appears in Google Calendar")
    logger.info("2. Integrate emergency notification into regular match processing")
    logger.info("3. Implement event-driven architecture for long-term solution")
    
    return True

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
